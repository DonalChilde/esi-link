from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from esi_link.v2 import example_requests
from esi_link.v2.esi_schema import (
    download_schema,
    save_indexed_schema_to_file,
    save_schemas_to_file,
)
from esi_link.v2.models import IndexedEsiSchema

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
    schema, timestamp = download_schema()
    if dir_out:
        date_str = timestamp.py_datetime().date().isoformat()
        raw_path, deref_path = save_schemas_to_file(schema, dir_out, date_str)
        console.print(
            f"ESI schema downloaded and saved to {raw_path} and {deref_path}."
        )
    indexed_schema = IndexedEsiSchema.from_raw_schema(schema, timestamp)
    save_indexed_schema_to_file(indexed_schema)
    console.print(f"ESI schema downloaded and saved to app directory.")


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
    ...
