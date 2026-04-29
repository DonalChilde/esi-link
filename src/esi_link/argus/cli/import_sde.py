"""This module provides cli commands for importing EVE Static Data Export (SDE) data into the Argus app.

The commands to download, unpack, export, and validate are provided elsewhere.
"""

import logging
from pathlib import Path
from typing import Annotated

import typer

from esi_link.argus.cli.helpers import get_argus_settings_from_context
from esi_link.argus.data.sde_data import ArgusSdeDataImporter

logger = logging.getLogger(__name__)

app = typer.Typer(
    no_args_is_help=True,
    help="Commands for importing EVE Static Data Export (SDE) data into the Argus app.",
)


@app.command()
def import_sde(
    ctx: typer.Context,
    input_path: Annotated[
        Path, typer.Argument(help="The path to the SDE data to import.")
    ],
):
    """Import the SDE data into the Argus app."""
    argus_settings = get_argus_settings_from_context(ctx)
    importer = ArgusSdeDataImporter(
        argus_settings.sde_directory, argus_settings.derived_data_directory
    )
    try:
        importer.import_sde(input_path)
        typer.echo(f"SDE data imported successfully from {input_path}.")
    except Exception as e:
        logger.exception(f"Failed to import SDE data from {input_path}. {e}")
        raise e
