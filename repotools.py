import json
import requests
import secrets

# if you're using a newer python than osx system python
# then reenable this, but i need this because old python < 2.7.10
requests.packages.urllib3.disable_warnings()

TOKEN = secrets.GITHUB_TOKEN

API_ROOT = "https://api.github.com"

DEFAULT_ARGS = {
    'API_ROOT': API_ROOT,
    'owner': 'khan'
}

def hit_github(endpoint, params={}, method="GET"):
    default_params = {'access_token': TOKEN}
    default_params.update(params)
    return requests.request(method, endpoint, params=default_params).json()

def get_branch(repo_dict):
    return repo_dict.get('default_branch')

def rawktopoke(endpoint, params=None, method="GET", *args, **kwargs):
    # get the raw requests response
    return octopoke(endpoint, params, method, raw_response=True, *args, **kwargs)

def octopoke(endpoint, params=None, method="GET", *args, **kwargs):
    """poke the github api and get json back

    kwargs:
        endpoint: what you see in the api docs, i.e.
            /repos/owner/repo
            except that the values should already be populated by you
        params: any query/post params
        method: GET by default, but whatever works
        raw_response: False by default, True returns request response
    """
    if not params:
        params = {}

    default_params = {'access_token': TOKEN}
    default_params.update(params)

    # don't do this, just use rawktopoke instead
    raw_response = kwargs.pop('raw_response', False)

    endpoint_params = {'API_ROOT': API_ROOT, 'endpoint': endpoint}
    api_endpoint = "{API_ROOT}{endpoint}".format(**endpoint_params)
    res = requests.request(method=method, url=api_endpoint, params=default_params, *args, **kwargs)
    if raw_response:
        return res
    else:
        return res.json()


def get_refs(repo_dict):
    endpoint = "{API_ROOT}/repos/{owner}/{repo}/git/refs/heads/{default_branch}"
    url_args = {
        'repo': repo_dict.get('name'),
        'default_branch': repo_dict.get('default_branch')
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

def arclint_at_ka():
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


def get_base_sha(owner, repo):
    api_endpoint = '/repos/{owner}/{repo}'.format(**{'owner':owner, 'repo': repo})
    repo_dict = octopoke(api_endpoint, {})
    # print repo_dict
    # default_branch = repo_dict.get('default_branch')
    ref_endpoint = '/repos/{owner}/{repo}/git/refs/heads/{ref}'.format(**{
        'owner': owner, 'repo':repo, 'ref': repo_dict.get('default_branch')})
    # print ref_endpoint
    refs = octopoke(ref_endpoint, {})
    return refs.get('object').get('sha')


def add_blob(owner, repo, filename):
    with open(filename) as f:
        contents = f.read()

    endpoint = "{API_ROOT}/repos/{owner}/{repo}/git/blobs"
    method = "POST"
    url_args = {
        'repo': repo,
        'owner': owner,
    }
    url_args.update(DEFAULT_ARGS)
    url = endpoint.format(**url_args)

    return hit_github(url, {'content': contents}, method="POST")


def obj_for_path(path):
    import hashlib
    with open(path) as f:
        contents = f.read()
        return {
            'type': 'blob',
            'mode': '100644',
            'path': path,
            'content': contents
        }


def add_tree_of_files(owner, repo, paths):
    """
    [{
        sha: '....',
        type: 'blob',
        mode: '100644',
        path: somepath
        },
    ...]
    """
    base_tree = get_base_sha(owner, repo)
    blobs = [obj_for_path(path) for path in paths]
    payload = {'base_tree': base_tree, 'tree': blobs }
    tree_endpoint = '/repos/{owner}/{repo}/git/trees'.format(owner=owner, repo=repo)
    return octopoke(tree_endpoint, method='POST', json=payload)


def commit_with_files(owner, repo, paths, message):
    """creates a commit without updating any refs"""
    base_tree = get_base_sha(owner, repo)
    tree = add_tree_of_files(owner, repo, paths)

    commit_endpoint = '/repos/{owner}/{repo}/git/commits'.format(owner=owner, repo=repo)
    payload = {'message': message, 'tree': tree.get('sha'), 'parents': [base_tree]}
    return octopoke(commit_endpoint, method='POST', json=payload)

def update_default_branch_with_commit(owner, repo, paths, message):
    """creates a commit on the default branch

    updates the default branch's ref to point to the new commit
    """
    api_endpoint = '/repos/{owner}/{repo}'.format(**{'owner':owner, 'repo': repo})
    repo_dict = octopoke(api_endpoint, {})

    commit = commit_with_files(owner,repo,paths, message)

    ref_endpoint = '/repos/{owner}/{repo}/git/refs/heads/{branch}'.format(
        **{'owner':owner, 'repo': repo, 'branch': repo_dict.get('default_branch')})
    octopoke(ref_endpoint, {}, method='PATCH', json={'sha': commit.get('sha')})


def main():
    with open('commit-msg') as f:
        commit_message = f.read()

    with open('repostoupdate.json') as f:
        repos = json.load(f)

        for repostring in repos:
            owner, repo = repostring.split('/')

            print "would now update {owner} // {repo}".format(owner=owner, repo=repo)
            update_default_branch_with_commit(owner, repo, ['.arclint', '.arcconfig'], commit_message)

if __name__ == '__main__':
    # main()
    pass

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
