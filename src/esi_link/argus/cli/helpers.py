"""Helper functions for the Argus CLI commands."""

from typing import cast

import typer
from eve_static_data import SdeYamlDatasetLoader
from eve_static_data.models.yaml_datasets import SdeInfoRoot
from rich.console import Console

from esi_link.argus.data.sde_data import ArgusSdeDataLoader
from esi_link.argus.settings import ArgusSettings


def get_argus_settings_from_context(ctx: typer.Context) -> ArgusSettings:
    """Helper function to get the Argus settings from the Typer context."""
    if ctx.obj is None or "argus-settings" not in ctx.obj:
        raise ValueError("Argus settings not found in context.")
    return cast(ArgusSettings, ctx.obj["argus-settings"])


# FIXME make a better Argus specific solution to checking for a valid SDE in the app directory.
def check_for_sde_before_use(argus_settings: ArgusSettings, console: Console):
    """Helper function to check for the presence of the SDE in the app directorybefore using it."""
    if not argus_settings.sde_directory.exists():
        raise ValueError(
            f"SDE directory not found at {argus_settings.sde_directory}. Please download the SDE and place it in the correct directory before using this command."
        )
    try:
        loader = SdeYamlDatasetLoader(argus_settings.sde_directory)
        if loader.file_type != ".json":
            raise ValueError(
                f"Expected json files in the SDE path, but found {loader.file_type} files. Please export to json first."
            )
    except FileNotFoundError as e:
        console.print(
            f"[red]SDE info file not found in {argus_settings.sde_directory}. Please ensure the SDE is correctly downloaded and imported using the CLI.[/red]"
        )
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Error loading SDE data: {e}[/red]")
        raise typer.Exit(code=1) from e
