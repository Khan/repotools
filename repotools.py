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

# gosh, so many apologies here, i started doing this "hit_github" approach
# and then realized what a bad idea it was and moved to octopoke and rawktopoke
# but by then the damage was already done. the refactor should be easy though.

def hit_github(endpoint, params={}, method="GET"):
    """No don't use this. i'm very sorry."""
    default_params = {'access_token': TOKEN}
    default_params.update(params)
    return requests.request(method, endpoint, params=default_params).json()


def get_branch(repo_dict):
    """a superfluous function"""
    return repo_dict.get('default_branch')


def rawktopoke(endpoint, params=None, method="GET", *args, **kwargs):
    """like octopoke but w/ a requests.Response object (for checkin' status codes, etc)"""
    return octopoke(endpoint, params, method, raw_response=True, *args, **kwargs)


def octopoke(endpoint, params=None, method="GET", *args, **kwargs):
    """poke the github api and get the json respose back as a dict

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
    """"""
    endpoint = "{API_ROOT}/repos/{owner}/{repo}/git/refs/heads/{default_branch}"
    url_args = {
        'repo': repo_dict.get('name'),
        'default_branch': repo_dict.get('default_branch')
    }
    url_args.update(DEFAULT_ARGS)

    url = endpoint.format(**url_args)
    return hit_github(url)


def get_tree(repo_dict):
    """returns a tree of blobs(files) for a given repository by looking
    at the most recent sha on its default branch

    repo_dict is what you get when you query
    {API_ROOT}/repos/{owner}/{repo}
    """
    endpoint = "{API_ROOT}/repos/{owner}/{repo}/git/trees/{sha}"
    url_args = {
        'repo': repo_dict['name'],
        'sha': get_refs(repo_dict).get('object').get('sha')
    }
    url_args.update(DEFAULT_ARGS)
    url = endpoint.format(**url_args)

    return hit_github(url)


def find_file_in(filename, repo_dict):
    """find a file in the tree of the newest commit of a repo's default branch

    NB: some bugs here, if the tree is too large, github will just ¯\_(ツ)_/¯
    and you need to find some other way to either page through the results or
    do some other chicanery to find that file (probably cloning the repo)

    repo_dict is the object you get from querying
    {API_ROOT}/repos/{owner}/{repo}
    """
    tree = get_tree(repo_dict).get('tree')
    return len([leaf for leaf in tree
                    if leaf['path'] == filename]) == 1


def arclint_at_ka():
    """check for .arclint on ka repos

    assuming you have two json files of repo data from the github api
    you can feed them to this and this will go through each of the
    repositories and look for .arclint in them.

    this was once a main() function, so it's not very smart or well
    written."""
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
    """for a given repo, get its default branch's latest commit/sha

    you can use this sha to build a commit on top of the repo.

    TODO: pass in a given branch (or better yet, ref), this assumes you're
    treating your main branch like refs/heads/<branch_name> which is sort
    of like cheating...
    """
    api_endpoint = '/repos/{owner}/{repo}'.format(**{'owner':owner, 'repo': repo})
    repo_dict = octopoke(api_endpoint, {})

    ref_endpoint = '/repos/{owner}/{repo}/git/refs/heads/{ref}'.format(**{
        'owner': owner, 'repo':repo, 'ref': repo_dict.get('default_branch')})

    refs = octopoke(ref_endpoint, {})
    return refs.get('object').get('sha')


def add_blob(owner, repo, filename):
    """you can use this to create a blob from a filename

    i don't recommend you use this actually, but it will do the right thing and
    return the sha of the blob's ref. it's on you to create a commit or other ref that
    will eventually point back to this in a way that is meaningful"""
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
    """a convenience method for add_tree_of_files.

    this assumes that you want 'path' to match on the repo. so that this file
    needs to be in the same spot relative to this script as it would be relative
    to the root of the target repository you are modifying.

    i.e. if the path is ".arclint" then you will get a "<repo>/.arclint" file.

    TODO: the mode should be derived by using the os module rather than
    always just being 'file'. """
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
    Creates a tree from a series of paths.

    The paths will be resolved, the files will be read and they will be
    added to the repository relative to its root in the same way that they
    are relative to the location of this script when it runs.

    TODO: make it possible to specify the location of the file independently
    from the destination (or at least have sensible defaults to override)
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


def commit_to_repos():
    """create a commit in many repositories with './commit-msg'
    as the content of the commit message.

    this will scan through './repostoupdae.json' (an array of
    form ['owner/repo_name',...]) and make the same commit over
    and over and over again in all of them.
    """
    with open('commit-msg') as f:
        commit_message = f.read()

    with open('repostoupdate.json') as f:
        repos = json.load(f)

        for repostring in repos:
            owner, repo = repostring.split('/')

            print "would now update {owner} // {repo}".format(owner=owner, repo=repo)
            update_default_branch_with_commit(owner, repo, ['.arclint', '.arcconfig'], commit_message)

def main():
    pass

if __name__ == '__main__':
    # TODO: import argparse up top and implement here
    main()
