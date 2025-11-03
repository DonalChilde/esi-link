"""CLI commands for ESI requests."""

import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from rich.console import Console
from rich.table import Table
from whenever import Instant
from yaml import safe_dump

from esi_link.cli.models import CliConfig
from esi_link.models import (
    AuthParams,
    EsiLinkError,
    EsiRequest,
    EsiRequests,
    HandlerConfig,
    ResponseHandlerProtocol,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def uuid():
    """Generate and display a new UUID."""
    import uuid

    console = Console()
    new_uuid = str(uuid.uuid4())
    console.print(f"[bold green]Generated UUID:[/bold green] {new_uuid}")
    console.print_json(data={"uuid": new_uuid})


@app.command(name="created-on")
def created_on_():
    """Display the current timestamp in ISO 8601 format."""
    console = Console()
    now = Instant.now()
    console.print(f"[bold green]Current Timestamp:[/bold green] {now.format_iso()}")
    console.print_json(data={"created_on": now.format_iso()})


@app.command(name="blank")
def blank_request(
    file_out: Annotated[
        Path,
        typer.Option(
            "-f",
            "--file-out",
            help="Path to save the blank ESI request template.",
            writable=True,
            dir_okay=False,
        ),
    ],
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            "-o",
            help="Whether to overwrite the file if it exists.",
        ),
    ] = False,
):
    """Display a blank ESI request template."""
    console = Console()
    blank_request = create_blank_request()
    requests = EsiRequests(
        requests_id=uuid4(),
        description="Blank ESI Request Template",
        requests={blank_request.request_id: blank_request},
    )
    console.rule("[bold green]Blank ESI Request Template[/bold green]")
    console.print(safe_dump(requests.model_dump(mode="json"), sort_keys=False))
    if file_out:
        requests.save_to_file(file_out, overwrite=overwrite)
        console.print(
            f"[bold green]Blank ESI request template saved to:[/bold green] {file_out.resolve()}"
        )


@app.command()
def examples(
    dir_out: Annotated[
        Path,
        typer.Argument(
            help="Directory to save example ESI requests to.",
            file_okay=False,
            writable=True,
        ),
    ],
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            "-o",
            help="Whether to overwrite the file if it exists.",
        ),
    ] = False,
):
    """Display example ESI requests."""
    console = Console()
    console.rule("[bold green]Example ESI Requests[/bold green]")
    blank_requests = [
        get_status_example(),
        get_market_orders_example(),
        get_universe_types_example(),
        post_universe_names_example(),
        get_character_attributes_example(),
    ]
    esi_requests = EsiRequests(
        requests_id=uuid4(),
        description="Example ESI requests",
        requests={req.request_id: req for req in blank_requests},
    )
    file_out = dir_out / "example-esi-requests.yaml"
    esi_requests.save_to_file(file_out, overwrite=overwrite)
    console.print(
        f"[bold green]Example ESI requests saved to:[/bold green] {file_out.resolve()}"
    )


@app.command()
def execute(
    ctx: typer.Context,
    path_in: Annotated[
        Path,
        typer.Argument(
            help="Path to load ESI requests from.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ],
):
    """Placeholder for executing ESI requests."""
    console = Console()
    console.rule("[bold green]Execute ESI Requests[/bold green]")
    try:
        requests = EsiRequests.load_from_file(path_in)
    except Exception as e:
        console.print(
            f"[bold red]Error loading ESI requests from {path_in}:[/bold red] {e}"
        )
        return
    console.print(
        f"[bold green]Loaded {len(requests.requests)} ESI requests from:[/bold green] {path_in}"
    )
    try:
        cli_config: CliConfig = ctx.obj
        esi_link = cli_config.esi_link
        if esi_link is None:
            raise EsiLinkError("Esi Link is not initialized in the CLI configuration.")
        result = asyncio.run(esi_link.execute_requests(requests=requests))
        for esi_response in result:
            if esi_response.http_response is None or esi_response.error_messages:
                # TODO refine this condition
                console.print(
                    f"[bold red]Error executing ESI request {esi_response.request.request_id}:[/bold red]"
                )
                if esi_response.http_response is None:
                    console.print("\t- No HTTP response received.")
                if esi_response.error_messages:
                    console.print("\t- Error Messages:")
                    for msg in esi_response.error_messages:
                        console.print(f"\t- {msg}")
            else:
                console.print(
                    f"[bold green]ESI request {esi_response.request.request_id} executed successfully with a {esi_response.http_response.status_code}[/bold green]"
                )
    except Exception as e:
        console.print(f"[bold red]Error executing ESI requests:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@app.command(name="handlers")
def handlers_(ctx: typer.Context):
    """Display available response handlers."""
    console = Console()
    console.rule("[bold green]Available Response Handlers[/bold green]")
    cli_config: CliConfig = ctx.obj
    esi_link = cli_config.esi_link
    if esi_link is None:
        console.print(
            "[bold red]Esi Link is not initialized in the CLI configuration.[/bold red]"
        )
        raise typer.Exit(code=1)
    handlers = esi_link.handler_manager.get_all_handlers()
    table = create_handlers_table(handlers)
    console.print(table)


def create_handlers_table(handlers: list[type[ResponseHandlerProtocol]]) -> Table:
    table = Table(show_lines=True, expand=True, show_header=False)
    table.add_column()
    table.add_column()

    for handler in handlers:
        config, description = handler.example_config()
        table.add_row("Name", f"[bold blue]{handler.name}[/bold blue]")
        table.add_row("Description", f"[green]{description}[/green]")
        table.add_row(
            "Example Config",
            f"[yellow]{safe_dump(config.model_dump(mode='json'), sort_keys=False)}[/yellow]",
        )
        table.add_row("", "")  # Empty row for spacing

    return table


def create_blank_request() -> EsiRequest:
    """Create a blank ESI request template."""
    return EsiRequest(
        request_id=uuid4(),
        operation_id="your_operation_id_here",
        path_parameters={"param1": "value1"},
        query_parameters={"param1": "value1"},
        auth_parameters=AuthParams(
            character_id=0, client_alias="your_client_alias_here"
        ),
        request_body={"key": "value"},
        headers={"Header-Name": "Header Value"},
        handlers=[
            HandlerConfig(name="your_handler_name", config={"key": "value"}),
            HandlerConfig(name="your_handler_name", config={"key": "value"}),
        ],
    )


def get_status_example() -> EsiRequest:
    """Example ESI request for GetStatus operation.

    An example of a simple request with no parameters.
    """
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetStatus",
        path_parameters={},
        query_parameters={},
        auth_parameters=None,
        request_body=None,
        headers={},
        handlers=[
            HandlerConfig(
                name="esi-link.esi_response_data_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}.json",
                    "overwrite": False,
                },
            ),
            HandlerConfig(
                name="esi-link.esi_response_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-response.json",
                    "overwrite": False,
                },
            ),
        ],
    )


def get_market_orders_example() -> EsiRequest:
    """Example ESI request for GetMarketsRegionIdOrders operation.

    An example of complex file path templating in response handlers.
    """
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdOrders",
        path_parameters={"region_id": 10000002},
        query_parameters={"order_type": "all", "type_id": 34},
        auth_parameters=None,
        request_body=None,
        headers={},
        handlers=[
            HandlerConfig(
                name="esi-link.esi_response_data_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-${REGION_ID}-${TYPE_ID}.json",
                    "overwrite": False,
                },
            ),
            HandlerConfig(
                name="esi-link.esi_response_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-response.json",
                    "overwrite": False,
                },
            ),
        ],
    )


def get_universe_types_example() -> EsiRequest:
    """Example ESI request for GetUniverseTypes operation.

    An example of multi page request handling.
    """
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetUniverseTypes",
        path_parameters={},
        query_parameters={},
        auth_parameters=None,
        request_body=None,
        headers={},
        handlers=[
            HandlerConfig(
                name="esi-link.esi_response_data_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}.json",
                    "overwrite": False,
                },
            ),
            HandlerConfig(
                name="esi-link.esi_response_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-response.json",
                    "overwrite": False,
                },
            ),
        ],
    )


def post_universe_names_example() -> EsiRequest:
    """Example ESI request for PostUniverseNames operation.

    An example of a POST request with a request body.
    """
    return EsiRequest(
        request_id=uuid4(),
        operation_id="PostUniverseNames",
        path_parameters={},
        query_parameters={},
        auth_parameters=None,
        request_body=[34, 35, 36],
        headers={},
        handlers=[
            HandlerConfig(
                name="esi-link.esi_response_data_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}.json",
                    "overwrite": False,
                },
            ),
            HandlerConfig(
                name="esi-link.esi_response_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-response.json",
                    "overwrite": False,
                },
            ),
        ],
    )


def get_character_attributes_example() -> EsiRequest:
    """Example ESI request for GetCharactersCharacterIdAttributes operation.

    An example of a request requiring authentication.
    """
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetCharactersCharacterIdAttributes",
        path_parameters={"character_id": 123456789},
        query_parameters={},
        auth_parameters=AuthParams(
            character_id=123456789, client_alias="your_client_alias_here"
        ),
        request_body=None,
        headers={},
        handlers=[
            HandlerConfig(
                name="esi-link.esi_response_data_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-${CHARACTER_ID}.json",
                    "overwrite": False,
                },
            ),
            HandlerConfig(
                name="esi-link.esi_response_to_file",
                config={
                    "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-response.json",
                    "overwrite": False,
                },
            ),
        ],
    )
