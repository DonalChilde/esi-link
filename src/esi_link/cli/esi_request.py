import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from rich.console import Console
from rich.panel import Panel
from whenever import Instant
from yaml import safe_dump

from esi_link.cli.models import CliConfig
from esi_link.models import (
    AuthParams,
    EsiLinkError,
    EsiRequest,
    EsiRequests,
    HandlerConfig,
    ResponseContext,
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


@app.command()
def blank_request():
    """Display a blank ESI request template."""
    console = Console()
    blank_request = create_blank_request()
    console.print(Panel.fit(str(blank_request), title="Blank ESI Request Template"))
    console.print(safe_dump(blank_request.model_dump(mode="json"), sort_keys=False))


@app.command()
def examples(
    file_out: Annotated[
        Path,
        typer.Option(
            "-f",
            "--file-path",
            help="Path to save example ESI requests to.",
        ),
    ] = Path("example_esi_requests.yaml"),
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
    blank_requests = [get_status_example(), get_market_orders_example()]
    esi_requests = EsiRequests(
        requests_id=uuid4(),
        description="Example ESI requests",
        requests={req.request_id: req for req in blank_requests},
    )
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
        response_context = ResponseContext()
        result = asyncio.run(
            esi_link.execute_requests(ctx=response_context, requests=requests)
        )
        for http_request, exception in result:
            if exception:
                console.print(
                    f"[bold red]Error executing ESI request {http_request.esi_request.request_id}:[/bold red] {exception}"
                )
            else:
                console.print(
                    f"[bold green]ESI request {http_request.esi_request.request_id} executed successfully[/bold green]"
                )
    except Exception as e:
        console.print(f"[bold red]Error executing ESI requests:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def create_blank_request() -> EsiRequest:
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
                name="esi-link.json_data_file",
                config={
                    "file_path": "{HOME}/tmp/esi-link-data/responses/{NOW}-{OPERATION_ID}.json",
                    "overwrite": False,
                },
            )
        ],
    )


def get_market_orders_example() -> EsiRequest:
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
                name="esi-link.json_data_file",
                config={
                    "file_path": "{HOME}/tmp/esi-link-data/responses/{NOW}-{OPERATION_ID}-{REGION_ID}-{TYPE_ID}.json",
                    "overwrite": False,
                },
            )
        ],
    )
