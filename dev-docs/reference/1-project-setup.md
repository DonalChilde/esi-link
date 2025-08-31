# Developer Setup

***NOTE: Assumes Linux OS***

***NOTE: Assumes use of uv***

## Existing project with repo

```bash
# get the url to the repository from github.
# from the new project directory...
git clone REPO_URL

# Setup a virtual environment
uv venv
uv sync

```

## New project with no existing repo

### Initial project layout



From the project directory:

- Initialize a project, uv init can be used for a quick start. [Creating uv projects](https://docs.astral.sh/uv/concepts/projects/init/#packaged-applications)

```bash
# for a simple layout:
uv init

# for a buildable project in a src dir:
uv init --package

# for a buildable library - --project with a py.typed
uv init --lib

# Setup a virtual environment
uv venv

# add a tests directory
mkdir ./tests
touch ./tests/__init__.py
mkdir ./tests/PROJECT_NAME
touch ./tests/PROJECT_NAME/__init__.py
```

- Add a LICENSE file to the project root
- Update the pyproject.toml project description
- Add/Update these entires in the pyproject.toml

```toml
# under the [Project] section.

# https://packaging.python.org/en/latest/specifications/license-expression/#specification
license = "LICENSE_EXPRESSION"
# https://packaging.python.org/en/latest/specifications/pyproject-toml/#license-files
license-files=[]
# https://packaging.python.org/en/latest/specifications/pyproject-toml/#dynamic
dynamic = ["version", "description"]

[project.scripts]
# script entry-points
# COMMAND_NAME = "PATH.TO.ENTRY.MODULE:ENTRY_FUNCTION"


[project.optional-dependencies]
foo_group = []

[project.dependency-groups]
# Dev dependencies
# https://docs.astral.sh/uv/concepts/projects/dependencies/#development-dependencies
# https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups
dev = [
  {include-group = "lint"},
  {include-group = "test"}
]
lint = []
test = []

# Documentation building dependencies like Sphinx
doc = []

[project.urls]
Documentation = "https://github.com/REPO_OWNER/PROJECT_NAME#readme"
# Documentation_rtd = "https://PROJECT_NAME.readthedocs.io"
Issues = "https://github.com/REPO_OWNER/PROJECT_NAME/issues"
Source = "https://github.com/REPO_OWNER/PROJECT_NAME>"

```
- Add project dependencies

```bash
# For a regular dependency
uv add typer

# For an optional dependency
uv add bar --optional foo_group

# For a dev dependency -> [dependency-groups]
uv add --dev ruff
# or
uv add --group lint ruff

```

- Sync the venv
```bash
uv sync
```

### Git setup

Assumes default branch name is main, adjust as needed

```bash
# you can set the global default branch
git config --global init.defaultBranch main
```
- add a .gitignore -> See [github .gitignore](https://github.com/github/gitignore) for examples
- init the git repository
```bash
git init --initial-branch=main
git add .
git commit -m "initial commit"
git tag -a VERSION_NUMBER -m "initial commit tag"
git branch dev

# Link local git repo to a separately created new GitHub project.
git remote add origin https://github.com/REPO_OWNER/PROJECT_NAME.git
git push -u origin main
git push origin VERSION_NUMBER
git push -u origin dev

# Checkout the dev branch and begin work!
git checkout dev

```




