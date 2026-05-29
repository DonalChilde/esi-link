# pyright: standard
import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from esi_link.rewrite import example_requests
from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.save_text_file import save_text_file
from esi_link.rewrite.helpers.settings_factories import (
    schema_cache_factory,
    token_store_factory,
    web_cache_factory,
)
from esi_link.rewrite.request.models import Request, RequestGroupRoot, RequestRoot
from esi_link.rewrite.request_dispatch_httpx2 import (
    dispatch_request_group,
    dispatch_requests,
)

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
            request = request_data
            response, failed_validations, failed_responses = asyncio.run(
                dispatch_requests(
                    requests={request.request_id: request},
                    schema_cache=schema_cache,
                    token_store=token_store,
                    web_cache=web_cache,
                )
            )

        else:
            request_group = request_data
            response, failed_validations, failed_responses = asyncio.run(
                dispatch_request_group(
                    request_group=request_group,
                    schema_cache=schema_cache,
                    token_store=token_store,
                    web_cache=web_cache,
                )
            )
    console.print(f"[green]Response:[/green] {response}")
    console.print(response)
    if failed_validations:
        console.print(f"[red]Failed Validations:[/red] {failed_validations}")
        console.print(failed_validations)
    if failed_responses:
        console.print(f"[red]Failed Responses:[/red] {failed_responses}")
        console.print(failed_responses)
