# dotfiles 

This repo is heavily inspired by:
 -  [Jess's repo](https://github.com/jessfraz/dotfiles)
 -  [Alrra's repo](https://github.com/alrra/dotfiles)
 -  [Mathias's repo](https://github.com/mathiasbynens/dotfiles)


**Table of Contents**

<!-- toc -->

- [About](#about)
  * [Installing](#installing)
  * [Customizing](#customizing)
- [Contributing](#contributing)
  * [Running the tests](#running-the-tests)

<!-- tocstop -->

## About

### Installing

```console
$ make
```

This will create symlinks from this repo to your home folder.

### Customizing
You can store additional things inside a .extra file. This will be sourced by `.bashrc` during init. 
You could place your git config data in it for example:

```
# Git credentials
# Not in the repository, to prevent people from accidentally committing under my name
GIT_AUTHOR_NAME="Leon Morten Richter"
GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
git config --global user.name "$GIT_AUTHOR_NAME"
GIT_AUTHOR_EMAIL="github@leonmortenrichter.de"
GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
git config --global user.email "$GIT_AUTHOR_EMAIL"
```

## Contributing

### Running the tests

The tests use [shellcheck](https://github.com/koalaman/shellcheck). You don't
need to install anything. They run in a container.

```console
$ make test
```
