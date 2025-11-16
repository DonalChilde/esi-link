"""CLI commands for interacting with the ESI schema."""

from typing import Annotated

import typer
from rich.console import Console, Group
from rich.panel import Panel

from esi_link.cli.helpers.format_operations_by_tag import (
    operations_by_tag_panels,
)
from esi_link.helpers.ensure_esi_schema import ensure_esi_schema
from esi_link.settings import get_settings

app = typer.Typer(no_args_is_help=True)


@app.command()
def status(
    force_update: Annotated[
        bool,
        typer.Option(
            "-f",
            "--force",
            help="Force update of the ESI schema from the remote source.",
            is_flag=True,
        ),
    ] = False,
):
    """Show information about the loaded ESI schema."""
    console = Console()
    console.rule("[bold green]ESI Schema Information[/bold green]")
    settings = get_settings()
    try:
        esi_schema = ensure_esi_schema(
            esi_schema_path=settings.esi_schema_path,
            esi_schema_url=settings.esi_schema_url,
            force_update=force_update,
        )
    except Exception as e:
        console.print(f"[red]Error loading ESI schema: {e}[/red]")
        raise typer.Exit(code=1) from e
    info_panel = Panel.fit(
        f"[bold]Title:[/bold] {esi_schema.info.get('title')}\n"
        f"[bold]Version:[/bold] {esi_schema.info.get('version')}\n"
        f"[bold]Download Date:[/bold] {esi_schema.download_date}\n"
        f"[bold]Number of Operations:[/bold] {len(esi_schema.operations)}",
        title="ESI Schema Info",
    )
    console.print(info_panel)


@app.command()
def operations():
    """Show available operations for the ESI schema."""
    console = Console()
    settings = get_settings()
    try:
        esi_schema = ensure_esi_schema(
            esi_schema_path=settings.esi_schema_path,
            esi_schema_url=settings.esi_schema_url,
            force_update=False,
        )
    except Exception as e:
        console.print(f"[red]Error loading ESI schema: {e}[/red]")
        raise typer.Exit(code=1) from e
    operation_panels = operations_by_tag_panels(esi_schema)
    ops_group = Group(*operation_panels)
    ops = Panel(ops_group, title="ESI Operations by Tag")

    console.print(ops)


@app.command()
def operation_raw(
    operation_id: Annotated[str, typer.Argument(help="The operation ID to show.")],
):
    """Show the raw JSON for a specific operation by its ID."""
    console = Console()
    console.rule(f"Fetching raw JSON for operation ID: [bold]{operation_id}[/bold]")
    settings = get_settings()
    try:
        esi_schema = ensure_esi_schema(
            esi_schema_path=settings.esi_schema_path,
            esi_schema_url=settings.esi_schema_url,
            force_update=False,
        )
    except Exception as e:
        console.print(f"[red]Error loading ESI schema: {e}[/red]")
        raise typer.Exit(code=1) from e
    indexed_operation = esi_schema.operations.get(operation_id)
    if indexed_operation is None:
        console.print(f"[red]Operation ID '{operation_id}' not found in the schema.")
        raise typer.Exit(code=1)
    console.print_json(data=indexed_operation.operation)
