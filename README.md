# ESI Link - Access the EVE Online ESI

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Project Description

esi-link is a library and cli for accessing the EVE Online ESI API. It enable the easy download and save to json of things like current market data, and character inventory. A command line interface is provided, as well as an API for use in third party programs.

## Quick Start

esi-link can make authenticated calls to the EVE ESI. If you want to make authenticated calls, follow the the instructions in the esi_auth Quick Start to set up an EVE Online application.

### Download the latest esi schema

from the terminal, run `esi-link schema download` to get the latest esi schema. This is required to be able to make requests to the EVE Esi.

### Set Up EVE Application

If you want to make authenticated requests, you must register an app with eve online.

First, create an EVE Online application at [EVE Developers](https://developers.eveonline.com/):

1. Create a new application
2. After your application has been created, view your application settings.
3. In that settings view, copy your application settings as json, and save to file.
4. You can use this file later to import your credentials to esi-link.

### Add your app credentials to esi-link

Add your credentials to esi-auth by running `esi-link auth creds add <path-to-credentials-file>`

Credentials must be in json format. 


### Authenticate Your First Character

From the terminal, run `esi-link auth tokens add` 

Click on the link in the terminal window, or copy and paste the url into your web browser.

Log into EVE Online, select your character, and approve the list of scopes.

### Test it out!

run `esi-link auth tokens list` to see the registered characters, 
and their character_id. You will need this character_id to make authenticated requests.

You can make some example requests to the esi by running `esi-link examples`

Assuming your app includes the `esi-skills.read_skills.v1` scope, you can try 
out an authenticated request by running `esi-link examples character-stats`


Try out the other example requests.



## Usage

## API Usage

## Installation

This project uses uv for development, and uv is also the easiest way to run the project.

> uv docs:  
> [Astral - uv](https://docs.astral.sh/uv/)  
> [https://docs.astral.sh/uv/concepts/tools/](https://docs.astral.sh/uv/concepts/tools/)  
> [https://docs.astral.sh/uv/reference/cli/#uv-tool](https://docs.astral.sh/uv/reference/cli/#uv-tool)  
> [https://docs.astral.sh/uv/pip/packages/#installing-a-package](https://docs.astral.sh/uv/pip/packages/#installing-a-package)  
> [https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-sources](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-sources)

To run with uv:

> Note the url format for tool install is the same as that for uv pip install:

```bash
# run esi-auth without installing
uvx --from git+https://github.com/DonalChilde/esi-link@main esi-link

# OR

# Install to Path
uv tool install --from git+https://github.com/DonalChilde/esi-link@main esi-link
# and run
esi-link ARGS
```

## Development

### Download the source code:

```bash
git clone https://github.com/DonalChilde/esi-link.git
cd esi-link
uv sync
# activate the venv if desired
source ./.venv/bin/activate
```

### Use as a dependency in another project:

```toml
# in your pyproject.toml file, for a uv managed project
dependencies = ["esi-link"]
[tool.uv.sources]
esi-link = { git = "https://github.com/DonalChilde/esi-link", branch = "main" }
```

### ruff settings for formatting and linting

```toml
[tool.ruff.lint]
select = ["B", "UP", "D", "DOC", "FIX", "I", "F401"]
# non-imperative-mood (D401)
ignore = ["D401", "D101"]
# extend-select = ["I"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
docstring-code-format = true
docstring-code-line-length = 88
```

## Contributing

## License

MIT License - see LICENSE file for details.

## Support

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
