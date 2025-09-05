from pathlib import Path
from typing import Annotated

import typer

from esi_link import CONFIG
from esi_link.cli.helpers import filter_if_silent
from esi_link.esi_schema.eve_openapi import EveOpenApi
from esi_link.esi_schema.operation_formatters.format_operations_by_tag import (
    format_operations_by_tag_string,
)
from esi_link.esi_schema.schema_store import SchemaStore

app = typer.Typer(no_args_is_help=True)


@app.command()
def update(
    ctx: typer.Context,
    file_path: Annotated[
        Path | None, typer.Option(help="Non-standard save path for the Schema Store.")
    ] = None,
):
    """Update an existing ESI schema, or download a new one."""
    msg = filter_if_silent(is_silent=False)
    try:
        if file_path is None:
            # work with app schema store
            store: SchemaStore | None = ctx.obj.schema_store
            if store is None:
                msg("No existing schema store found, downloading new schema.")
                store_path = CONFIG.schema_dir / "schema_store.json"
                msg(f"Downloading schema to {store_path}")
                store = SchemaStore.from_download(store_path=store_path)
                msg("Download complete.")
            else:
                msg(f"Updating existing schema store at {store._store_path}.")  # type: ignore
                store.update()
                msg("Download complete.")
        else:
            # work with a schema store outside of the app
            store_path = file_path
            if store_path.is_file():
                msg(f"Attempting to update existing schema store at {store_path}.")
                store = SchemaStore(store_path=store_path)
                msg(f"Downloading schema to {store_path}")
                store.update()
                msg("Download complete.")
            else:
                if store_path.is_dir():
                    raise ValueError(
                        f"Provided schema store path {store_path} is a directory."
                    )
                msg(f"Downloading schema to {store_path}")
                store = SchemaStore.from_download(store_path=store_path)
                msg("Download complete.")
    except Exception as e:
        typer.echo(f"Error updating schema: {e}")
        raise typer.Exit(code=1) from e
    msg("Schema updated successfully.")


@app.command()
def status(ctx: typer.Context):
    """Show the current status of the ESI schema."""
    msg = filter_if_silent(is_silent=False)
    msg("Current status of the ESI schema:")
    if ctx.obj.schema_store:
        store = ctx.obj.schema_store
        msg(f"  Schema ID: {store._store_data.id_}")
        msg(f"  Download Date: {store._store_data.download_date}")
    else:
        msg("No schema store found.")


@app.command()
def operations(ctx: typer.Context):
    """Show available operations for the ESI schema."""
    store = ctx.obj.schema_store
    eve_api = EveOpenApi.from_schema_store(store)
    typer.echo(format_operations_by_tag_string(eve_api))
