"""CLI commands related to the ESI schema."""

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON
from rich.table import Table
from whenever import Instant

from esi_link.cli.helpers import get_settings_from_context
from esi_link.cli.schema_display_helpers import display_operations_by_tag
from esi_link.helpers.datetime_filename import file_safe_iso_datetime_string
from esi_link.helpers.download_schema import (
    download_schema,
    download_schema_changelog,
)
from esi_link.helpers.eve_dates import current_compatibility_date
from esi_link.helpers.indexed_operation_summary import (
    collect_operation_summaries,
    summaries_by_tag,
)
from esi_link.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.helpers.save_text_file import save_text_file
from esi_link.schema.schema_manager import SchemaManager

app = typer.Typer(no_args_is_help=True, help="Commands related to the ESI schema.")


@app.command()
def download(
    ctx: typer.Context,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "-c",
            "--compatibility-date",
            help="The compatibility date to use for the ESI schema download. Defaults to the current compatibility date.",
        ),
    ] = None,
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
    overwrite: Annotated[
        bool,
        typer.Option(
            "-o",
            "--overwrite",
            help="Whether to overwrite existing files when saving the downloaded ESI schema. Defaults to False.",
        ),
    ] = False,
):
    """Download the ESI schema to the app directory."""
    console = Console()
    compat_date = compatibility_date or current_compatibility_date()
    console.print(f"Downloading ESI schema for compatibility date {compat_date}...")
    settings = get_settings_from_context(ctx)
    schema_download = asyncio.run(
        download_schema(compatibility_date=compat_date, url=settings.esi_schema_url)
    )
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    schema_manager.add_schema(schema_download.raw_schema, schema_download.download_date)
    console.print(f"ESI schema downloaded and added to app schema store.")
    if dir_out:
        safe_date = file_safe_iso_datetime_string(
            schema_download.download_date.format_iso()
        )
        raw_schema = schema_download.raw_schema
        raw_path = save_text_file(
            text=json.dumps(raw_schema, indent=2),
            output_dir=dir_out,
            file_name=f"esi_schema_raw_{safe_date}.json",
            overwrite=overwrite,
        )
        deref_path = save_text_file(
            text=json.dumps(resolve_internal_refs(raw_schema, raw_schema), indent=2),
            output_dir=dir_out,
            file_name=f"esi_schema_dereferenced_{safe_date}.json",
            overwrite=overwrite,
        )

        console.print(
            f"ESI schema downloaded and saved to {raw_path} and {deref_path}."
        )


@app.command()
def changelog(
    ctx: typer.Context,
    dir_out: Annotated[
        Path | None,
        typer.Option(
            "-d",
            "--dir-out",
            help="Directory to save the downloaded ESI schema Changelog as a json file. "
            "The filename will be `schema-changelog-<download_date>.json`. Defaults to None.",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "-o",
            "--overwrite",
            help="Whether to overwrite existing files when saving the downloaded ESI schema changelog. Defaults to False.",
        ),
    ] = False,
):
    """Show the changelog for the ESI schema."""
    console = Console()
    console.print("Fetching ESI schema changelog...")
    settings = get_settings_from_context(ctx)
    changelog = asyncio.run(
        download_schema_changelog(url=settings.esi_schema_changelog_url)
    )
    console.print(JSON.from_data(changelog))
    if dir_out:
        file_path = save_text_file(
            text=json.dumps(changelog, indent=2),
            output_dir=dir_out,
            file_name=f"schema-changelog-{file_safe_iso_datetime_string(Instant.now().format_iso())}.json",
            overwrite=overwrite,
        )
        console.print(f"ESI schema changelog saved to {file_path}.")


@app.command()
def operations(
    ctx: typer.Context,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "-c",
            "--compatibility-date",
            help="The compatibility date to load from the schema manager. If None, the "
            "most recent schema will be used. Defaults to None.",
        ),
    ] = None,
    timestamp: Annotated[
        int | None,
        typer.Option(
            "-t",
            "--timestamp",
            help="Used in conjunction with the compatibility date option. The timestamp "
            "to use for the ESI schema download. Used to pick between multiple copies of "
            "the same compatibility date. If None, the most recent version of the schema "
            "matching the compatibility date will be used. Defaults to None.",
        ),
    ] = None,
    dir_out: Annotated[
        Path | None,
        typer.Option(
            help="Directory to save the list of operations to as a json file. The file "
            "name will be `operations-<compatibility_date>-<timestamp>.json`. If not "
            "provided, the operations will be printed to the console."
        ),
    ] = None,
):
    """List the operations available in the ESI schema."""
    console = Console()
    settings = get_settings_from_context(ctx)
    store_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    try:
        schema = get_schema(
            schema_manager=store_manager,
            compatibility_date=compatibility_date,
            timestamp=timestamp,
        )
    except Exception as e:
        console.print(f"Error loading schema: {str(e)}")
        raise typer.Exit(code=1) from e

    operation_summaries = collect_operation_summaries(schema)
    summaries_by_tag_dict = summaries_by_tag(operation_summaries)
    console.print(
        f"Collected {len(operation_summaries)} operations from the ESI schema version {schema.compatibility_date} downloaded at {schema.download_date}."
    )
    if dir_out:
        file_path = save_text_file(
            text=json.dumps(operation_summaries, indent=2),
            output_dir=dir_out,
            file_name=f"operations-{schema.compatibility_date}-{schema.download_date.timestamp()}.json",
            overwrite=True,
        )
        console.print(f"Operation summaries saved to {file_path}.")
    else:
        display_operations_by_tag(summaries_by_tag_dict)


@app.command()
def available_schemas(ctx: typer.Context):
    """List the available ESI schemas in the schema store."""
    console = Console()
    settings = get_settings_from_context(ctx)
    store_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    schemas = store_manager.available_schemas()
    table = Table(title="Available ESI Schemas")
    table.add_column("Compatibility Date", style="cyan")
    table.add_column("Download Date", style="magenta")
    table.add_column("Timestamp", style="yellow")
    for schema in schemas:
        table.add_row(schema[0], schema[2], str(schema[1]))
    console.print(table)


def get_schema(
    schema_manager: SchemaManager, compatibility_date: str | None, timestamp: int | None
):
    """Helper function to get the ESI schema from the schema manager based on the compatibility date and timestamp."""
    if compatibility_date:
        if timestamp:
            schema = schema_manager.get_schema_for_date(
                compatibility_date=compatibility_date, timestamp=timestamp
            )
        else:
            schema = schema_manager.get_latest_schema(
                compatibility_date=compatibility_date
            )
    else:
        schema = schema_manager.get_latest_schema(compatibility_date=None)

    return schema
