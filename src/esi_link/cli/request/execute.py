# pyright: standard
import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from whenever import Instant

from esi_link.auth.token_store import TokenStore
from esi_link.cli.helpers import get_esi_link_settings_from_context
from esi_link.helpers.file_safe_string import file_safe_string
from esi_link.helpers.save_text_file import save_text_file
from esi_link.helpers.settings_factories import (
    schema_cache_factory,
    token_store_factory,
    web_cache_factory,
)
from esi_link.protocols.cache_manager import CacheManagerProtocol
from esi_link.request.models import (
    Request,
    RequestGroup,
    RequestGroupRoot,
    RequestRoot,
)
from esi_link.request_dispatch import (
    dispatch_request,
    dispatch_request_group,
)
from esi_link.response.models import Response, ResponseGroup
from esi_link.response.response_factories import (
    response_group_to_response_data_group,
)
from esi_link.runtime.models import FailedRuntimeResponse
from esi_link.schema.schema_cache import SchemaCache
from esi_link.validation.models import InvalidRequest

app = typer.Typer(no_args_is_help=True)


@app.command()
def execute(
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
    """Execute a request or request group from a JSON file."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    file_name = request_file.name
    if file_name.endswith("-request.json"):
        request_data = RequestRoot.model_validate_json(request_file.read_text()).root
    elif file_name.endswith("-request-group.json"):
        request_data = RequestGroupRoot.model_validate_json(
            request_file.read_text()
        ).root
    else:
        console.print(
            f"[red]The request file name must end with either '-request.json' or '-request-group.json' to indicate whether it contains a Request or RequestGroup object.[/red]"
        )
        raise typer.Exit(code=1)
    token_store = token_store_factory(settings)
    schema_cache = schema_cache_factory(settings)
    web_cache = web_cache_factory(settings)
    with token_store:
        if isinstance(request_data, Request):
            response = asyncio.run(
                dispatch_request(
                    request=request_data,
                    schema_cache=schema_cache,
                    token_store=token_store,
                    web_cache=web_cache,
                )
            )

        else:
            response = asyncio.run(
                dispatch_request_group(
                    request_group=request_data,
                    schema_cache=schema_cache,
                    token_store=token_store,
                    web_cache=web_cache,
                )
            )
    console.print(response)
