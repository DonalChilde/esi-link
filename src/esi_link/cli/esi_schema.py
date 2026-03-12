"""CLI commands related to the ESI schema."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from esi_link import example_requests
from esi_link.cli.helpers import get_settings_from_context
from esi_link.esi_schema import (
    add_schema_to_store,
    download_schema,
    load_schema_store,
    save_schemas_to_file,
)
from esi_link.helpers.eve_dates import compatibility_date
from esi_link.helpers.indexed_operation_helpers import (
    IndexedOperationSummary,
    collect_operation_summaries,
    summaries_by_tag,
)
from esi_link.helpers.schema_display_helpers import display_operations_by_tag
from esi_link.models import IndexedEsiSchema
from esi_link.schema_manager import SchemaManager

app = typer.Typer(no_args_is_help=True, help="Commands related to the ESI schema.")


@app.command()
def status(ctx: typer.Context):
    """Show the status of the ESI schema."""
    console = Console()
    console.print("Fetching ESI schema status...")
    status_request = example_requests.esi_status()
    ...


@app.command()
def download(
    ctx: typer.Context,
    dir_out: Annotated[
        Path | None,
        typer.Option(
            "-d",
            "--dir-out",
            help="Path to save the downloaded ESI schema to json files. Both a raw, "
            "and dereferenced version of the schema will be saved. If not provided, only "
            "the schema in the app directory will be updated. Defaults to None.",
        ),
    ] = None,
):
    """Download the ESI schema to the app directory."""
    console = Console()
    compat_date = compatibility_date()
    settings = get_settings_from_context(ctx)
    schema_manager = SchemaManager(settings=settings)
    schema_download = schema_manager.download_schema(compatibility_date=compat_date)
    indexed_schema = schema_manager.transform_schema(
        raw_schema=schema_download.raw_schema,
        download_date=schema_download.download_date,
    )
    schema_manager.add_schema(indexed_schema)

    if dir_out:
        raw_path, deref_path = save_schemas_to_file(
            schema_download.raw_schema,
            dir_out,
            compat_date,
        )
        console.print(
            f"ESI schema downloaded and saved to {raw_path} and {deref_path}."
        )

    console.print(f"ESI schema downloaded and added to app schema store.")


@app.command()
def changelog(
    ctx: typer.Context,
    file_out: Annotated[
        Path | None,
        typer.Option(
            "-f",
            "--file-out",
            help="Path to save the downloaded ESI schema Changelog to a json file. Defaults to None.",
        ),
    ] = None,
):
    """Show the changelog for the ESI schema."""
    console = Console()
    console.print("Fetching ESI schema changelog...")
    changelog_request = example_requests.esi_changelog()
    ...


@app.command()
def operations(
    ctx: typer.Context,
    path_out: Annotated[
        Path | None,
        typer.Option(
            help="Path to save the list of operations to as a json file. If not provided, the operations will be printed to the console."
        ),
    ] = None,
):
    """List the operations available in the ESI schema."""
    console = Console()
    # TODO Needs refinement.
    settings = get_settings_from_context(ctx)
    schema_store = load_schema_store(schema_store_path=settings.schema_store_path)
    latest_schema = schema_store.latest_schema()
    if not latest_schema:
        console.print(
            "No ESI schemas found in the schema store. Please download a schema first."
        )
        return
    operation_summaries = collect_operation_summaries(latest_schema)
    summaries_by_tag_dict = summaries_by_tag(operation_summaries)
    console.print(
        f"Collected {len(operation_summaries)} operations from the ESI schema version {latest_schema.version}."
    )
    if path_out:
        path_out.parent.mkdir(parents=True, exist_ok=True)
        path_out.write_text(json.dumps(summaries_by_tag_dict, indent=2))
        console.print(f"Operation summaries saved to {path_out}.")
    else:
        display_operations_by_tag(summaries_by_tag_dict)
