# pyright: standard
import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from whenever import Instant

from esi_link.rewrite import example_requests
from esi_link.rewrite.auth.oauth_metadata import OAuthMetadataDiskCache
from esi_link.rewrite.auth.token_store import TokenStore
from esi_link.rewrite.auth.token_tool import TokenTool
from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.file_safe_string import file_safe_string
from esi_link.rewrite.helpers.save_text_file import save_text_file
from esi_link.rewrite.helpers.settings_factories import (
    schema_cache_factory,
    token_store_factory,
    web_cache_factory,
)
from esi_link.rewrite.protocols.cache_manager import CacheManagerProtocol
from esi_link.rewrite.request.models import (
    Request,
    RequestGroup,
    RequestGroupRoot,
    RequestRoot,
)
from esi_link.rewrite.request_dispatch_httpx2 import (
    _dispatch_requests,
    dispatch_request,
    dispatch_request_group,
)
from esi_link.rewrite.response.models import Response
from esi_link.rewrite.runtime.models import FailedRuntimeResponse
from esi_link.rewrite.schema.schema_cache import SchemaCache
from esi_link.rewrite.settings import EsiLinkSettings
from esi_link.rewrite.validation.models import FailedRequestValidation

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
):
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
            _make_request(
                token_store=token_store,
                schema_cache=schema_cache,
                web_cache=web_cache,
                request=request_data,
            )

        else:
            _make_request_group(
                token_store=token_store,
                schema_cache=schema_cache,
                web_cache=web_cache,
                request_group=request_data,
            )


def _make_request(
    token_store: TokenStore,
    schema_cache: SchemaCache,
    web_cache: CacheManagerProtocol,
    request: Request,
) -> None:
    """Make a single request."""
    response = asyncio.run(
        dispatch_request(
            request=request,
            schema_cache=schema_cache,
            token_store=token_store,
            web_cache=web_cache,
        )
    )
    console = Console()
    if isinstance(response, Response):
        console.print(f"[green]Response:[/green] {response}")
        console.print(response)
    elif isinstance(response, FailedRequestValidation):
        console.print(f"[red]Failed Validation:[/red] {response}")
        console.print(response)
    elif isinstance(response, FailedRuntimeResponse):
        console.print(f"[red]Failed Response:[/red] {response}")
        console.print(response)


def _make_request_group(
    token_store: TokenStore,
    schema_cache: SchemaCache,
    web_cache: CacheManagerProtocol,
    request_group: RequestGroup,
    output_directory: Path | None = None,
) -> None:
    """Make a group of requests."""
    response_group = asyncio.run(
        dispatch_request_group(
            request_group=request_group,
            schema_cache=schema_cache,
            token_store=token_store,
            web_cache=web_cache,
        )
    )
    console = Console()
    console.print(f"[green]Response Group:[/green]")
    console.print(f"Out of {len(request_group.requests)} requests:")
    console.print(f"  Successful responses: {len(response_group.responses)}")
    console.print(
        f"  Failed validations: {len(response_group.failed_request_validations)}"
    )
    console.print(f"  Failed responses: {len(response_group.failed_runtime_responses)}")
    if output_directory is not None:
        now = file_safe_string(f"{Instant.now()}")
        file_name = f"{request_group.group_id}-{now}-response-group.json"
        saved = save_text_file(
            text=response_group.to_string(indent=4),
            output_dir=output_directory,
            file_name=file_name,
            overwrite=False,
        )
        console.print(f"[green]Response group saved to:[/green] {saved}")
    else:
        console.print(response_group)
