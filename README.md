# ka repo tools

n.b. this is not at all productized

A series of useful methods which you can use to run audits across a github organization.

It supports two main use cases:

1. looking for a file, missing or present in a repository.
2. committing a series of files to a repository.

presumably if you are trying to check for file's compliance in a repository, you can extend
what you find here. More likely, though, you're better off just creating a new commit if you
just want to blast the file away with the updates. The commit will register the delta between
the two files anyway.

much of this was implemented while learning the github api, so its structure is not
particularly well thought out. if you are trying to figure out how something works, you may
want to look at the two methods:

* `commit_to_repos`
* `arclint_at_ka'

and unwind that virtual call stack. `commit_to_repos` is better to look at since i already knew
a bit more about what was going on at the time. `arclint_at_ka` is a bit confused, but i mean,
it clearly gets the job done.

A caveat: in the world of github, a private fork is listed as a 'source' repo.

## "installing"

    virtualenv env
    . ./env/bin/activate
    pip install -r requirements.txt

then you will need to create a [github access token](https://github.com/settings/tokens) and put it in `secrets.py`

you will want the following permissions (most likely)

* read:org
* repo
* user

then modify `main` as you need to (or add in argparse nonsense)


## other things

are those tests? oh wait, there is no coverage

## license

(c) marcos ojeda, 2015, mit or bsd or whatever licensed
