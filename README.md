# ESI Link - Access the EVE Online ESI

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Project Description

esi-link is a library and cli for accessing the EVE Online ESI API. It enable the easy download and save to json of things like current market data, and character inventory. A command line interface is provided, as well as an API for use in third party programs.

## Quick Start

esi-link uses [esi-auth](https://github.com/DonalChilde/esi-auth) to manage authenticated calls to the EVE ESI. If you want to make authenticated calls, follow the the instructions in the esi_auth Quick Start to set up an EVE Online application.

TODO - Usable quick start and usage instructions.

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
