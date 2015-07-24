import urllib2
import json
import secrets
import requests

# please reenable this (just not for me)
requests.packages.urllib3.disable_warnings()

TOKEN = secrets.GITHUB_TOKEN

API_ROOT = "https://api.github.com"

DEFAULT_ARGS = {
    'API_ROOT': API_ROOT,
    'owner': 'khan'
}

def hit_github(endpoint, params={}):
    default_params = {'access_token': TOKEN}
    default_params.update(params)
    return requests.get(endpoint, default_params).json()

def get_branch(repo_dict):
    return repo_dict.get('default_branch')

def get_refs(repo_dict):
    endpoint = "{API_ROOT}/repos/{owner}/{repo}/git/refs/heads/{default_branch}"
    url_args = {
        'repo': repo_dict.get('name'),
        'default_branch': get_branch(repo_dict)
    }
    url_args.update(DEFAULT_ARGS)

    url = endpoint.format(**url_args)
    return hit_github(url)

def get_tree(repo_dict):
    endpoint = "{API_ROOT}/repos/{owner}/{repo}/git/trees/{sha}"
    url_args = {
        'repo': repo_dict['name'],
        'sha': get_refs(repo_dict).get('object').get('sha')
    }
    url_args.update(DEFAULT_ARGS)
    url = endpoint.format(**url_args)

    return hit_github(url)

def find_file_in(filename, repo_dict):
    tree = get_tree(repo_dict).get('tree')
    return len([leaf for leaf in tree
                    if leaf['path'] == filename]) == 1

def main():
    with open('karepos.json') as f:
        repodata = json.load(f)
    with open('karepos2.json') as f:
        repodata.extend(json.load(f))

    for repo in repodata:
        if not repo['private']:
            if not find_file_in('.arclint', repo):
                truant_repo = repo.get('name')
                message = ('missing .arclint in {repo_name} (public)\n' +
                            '  -> {repo_url}')
                msg_args = {
                    'repo_name': repo['name'],
                    'repo_url': repo['html_url']
                }
                print message.format(**msg_args)


if __name__ == '__main__':
    main()
# def repo_tree(repo, sha):
#     org = "khan"
#     return API_ROOT + "/repos/%s/%s/git/trees/%s" % (org, repo, sha)


# scan through json files:
# 1.. get default branch
# 2.. then hit
#   GET /repos/:owner/:repo/git/refs/:ref
#   where :ref == something like heads/default_branch
# 3.. then get
#   {
#   "ref": "refs/heads/gh-pages",
#   "url": "https://api.github.com/repos/Khan/thumbnail-sketches/git/refs/heads/gh-pages",
#   "object": {
#     "sha": "80c9dfc468e2a58d44856d3b33a607f9203b1f97",
#     "type": "commit",
#     "url": "https://api.github.com/repos/Khan/thumbnail-sketches/git/commits/{sha}"
#   }
# }

# 4.. with sha, then get the tree
#   GET /repos/:owner/:repo/git/trees/:sha

# 5.. iterate over result['tree'] which is an array of
# objects with a 'path' key. filter to see if path contains whatever
#
# 6. report if not .arclint not present
