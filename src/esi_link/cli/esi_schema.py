from typing import Annotated

import typer
from rich.console import Console, Group
from rich.panel import Panel

from esi_link.cli.models import CliConfig
from esi_link.format_operations_by_tag import (
    operations_by_tag_panels,
)

app = typer.Typer(no_args_is_help=True)

# TODO add raw json output of operation, with path and method.


@app.command()
def operations(ctx: typer.Context):
    """Show available operations for the ESI schema."""
    console = Console()
    cli_config: CliConfig = ctx.obj
    if (
        cli_config.esi_link_config is None
        or cli_config.esi_link_config.esi_schema is None
    ):
        console.print("[red]ESI schema is not loaded in the configuration.")
        raise typer.Exit(code=1)
    operation_panels = operations_by_tag_panels(cli_config.esi_link_config.esi_schema)
    ops_group = Group(*operation_panels)
    ops = Panel(ops_group, title="ESI Operations by Tag")

    console.print(ops)


@app.command()
def operation_raw(
    ctx: typer.Context,
    operation_id: Annotated[str, typer.Argument(help="The operation ID to show.")],
):
    """Show the raw JSON for a specific operation by its ID."""
    console = Console()
    console.rule(f"Fetching raw JSON for operation ID: [bold]{operation_id}[/bold]")
    cli_config: CliConfig = ctx.obj
    if (
        cli_config.esi_link_config is None
        or cli_config.esi_link_config.esi_schema is None
    ):
        console.print("[red]ESI schema is not loaded in the configuration.")
        raise typer.Exit(code=1)
    esi_schema = cli_config.esi_link_config.esi_schema
    indexed_operation = esi_schema.operations.get(operation_id)
    if indexed_operation is None:
        console.print(f"[red]Operation ID '{operation_id}' not found in the schema.")
        raise typer.Exit(code=1)
    console.print_json(data=indexed_operation.operation)
