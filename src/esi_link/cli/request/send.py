"""This module contains the implementation of the `send` command for the ESI Link CLI.

This command allows users to send a request or request group defined in a JSON file and
receive the response.
"""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from yaml import safe_load

from esi_link.cli.helpers import get_esi_link_settings_from_context
from esi_link.helpers.settings_factories import (
    schema_cache_factory,
    token_store_factory,
    web_cache_factory,
)
from esi_link.request.models import Request, RequestGroup
from esi_link.request_dispatch import (
    dispatch_request,
    dispatch_request_group,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def send(
    ctx: typer.Context,
    request_file: Annotated[
        Path,
        typer.Argument(
            help="The path to the request file to execute. This should be a JSON file containing either a Request or RequestGroup object.",
            file_okay=True,
            dir_okay=False,
            exists=True,
            readable=True,
        ),
    ],
    output_directory: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output-directory",
            help="The directory to save the response file to. If not provided, the response will not be saved to disk.",
            file_okay=False,
            dir_okay=True,
            exists=True,
            writable=True,
        ),
    ] = None,
    file_name: Annotated[
        str | None,
        typer.Option(
            "--file-name",
            help="The name to use for the response file. If not provided, a name will be generated based on the request ID and creation date.",
        ),
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Whether to save debug information.")
    ] = False,
    pipe_output: Annotated[
        bool,
        typer.Option(
            "--pipe",
            help="Whether to pipe the response output to stdout. If set, the response objects will be printed without extra text.",
        ),
    ] = False,
) -> None:
    """Send a request or request group from a JSON file."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    loaded_request = _load_request_from_file(request_file)
    token_store = token_store_factory(settings)
    schema_cache = schema_cache_factory(settings)
    web_cache = web_cache_factory(settings)
    with token_store:
        if isinstance(loaded_request, Request):
            response = asyncio.run(
                dispatch_request(
                    request=loaded_request,
                    schema_cache=schema_cache,
                    token_store=token_store,
                    web_cache=web_cache,
                )
            )

        else:
            response = asyncio.run(
                dispatch_request_group(
                    request_group=loaded_request,
                    schema_cache=schema_cache,
                    token_store=token_store,
                    web_cache=web_cache,
                )
            )
    console.print(response)


def _load_request_from_file(request_file: Path) -> Request | RequestGroup:
    """Load a Request or RequestGroup object from a JSON or YAML file."""
    if request_file.stem.endswith("-request"):
        if request_file.suffix == ".json":
            request_data = Request.from_json_string(request_file.read_text())
        elif request_file.suffix in [".yaml", ".yml"]:
            request_object = safe_load(request_file.read_text())
            request_data = Request.from_object(request_object)
        else:
            raise ValueError(
                f"Unsupported file format: {request_file.suffix}. Supported formats are .json, .yaml, and .yml."
            )
    elif request_file.stem.endswith("-request-group"):
        if request_file.suffix == ".json":
            request_data = RequestGroup.from_json_string(request_file.read_text())
        elif request_file.suffix in [".yaml", ".yml"]:
            request_object = safe_load(request_file.read_text())
            request_data = RequestGroup.from_object(request_object)
        else:
            raise ValueError(
                f"Unsupported file format: {request_file.suffix}. Supported formats are .json, .yaml, and .yml."
            )
    else:
        raise ValueError(
            f"The request file name must end with either '-request.json' or '-request-group.json' to indicate whether it contains a Request or RequestGroup object."
        )
    return request_data
