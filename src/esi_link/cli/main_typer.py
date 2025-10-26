"""Command-line interface."""

import logging
from pathlib import Path
from time import perf_counter, perf_counter_ns
from typing import Annotated

import typer
from rich.console import Console
from typer import get_app_dir

from esi_link.cli.esi_request import app as esi_request_app
from esi_link.cli.esi_schema import app as esi_schema_app
from esi_link.cli.models import CliConfig
from esi_link.download_esi_schema import download_esi_schema
from esi_link.esi_link import USER_AGENT
from esi_link.esi_link_factory import esi_link_factory
from esi_link.logging_config import setup_logging
from esi_link.models import EsiLinkConfig, EsiSchema

logger = logging.getLogger(__name__)
APP_NAMESPACE = "pfmsoft"
APP_NAME = "Esi Link"

_app_dir = get_app_dir(app_name=f"{APP_NAMESPACE}-{APP_NAME}")
_log_dir = Path(_app_dir) / "logs"
setup_logging(log_dir=_log_dir)
ESI_LINK_CONFIG_PATH = Path(_app_dir) / "esi_link_config.json"

app = typer.Typer(no_args_is_help=True)
app.add_typer(esi_schema_app, name="schema")
app.add_typer(esi_request_app, name="requests")


@app.callback(invoke_without_command=True)
def default_options(
    ctx: typer.Context,
    debug: Annotated[bool, typer.Option(help="Enable debug output.")] = False,
    verbosity: Annotated[int, typer.Option("-v", help="Verbosity.", count=True)] = 1,
    silent: Annotated[
        bool,
        typer.Option(help="Enable silent mode. Only results and errors will be shown."),
    ] = False,
    config_path: Annotated[
        Path,
        typer.Option(
            help="Path to Esi Link configuration file.",
            exists=False,
            dir_okay=False,
            writable=True,
            readable=True,
        ),
    ] = ESI_LINK_CONFIG_PATH,
    esi_schema_url: Annotated[
        str | None,
        typer.Option(
            help="Non-standard URL to download ESI schema from.",
        ),
    ] = None,
    force_schema_update: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Force update of ESI schema from URL, even if already present in configuration.",
        ),
    ] = False,
):
    """Esi Link Command Line Interface.

    Insert pithy saying here
    """
    console = Console()
    ctx.ensure_object(CliConfig)
    cli_config: CliConfig = ctx.obj
    cli_config.start_time = perf_counter_ns()
    cli_config.debug = debug
    cli_config.verbosity = verbosity
    cli_config.silent = silent
    cli_config.esi_link_config_path = config_path

    # Complete the initialization of the configuration
    _init_config(
        ctx,
        config_path=config_path,
        esi_schema_url=esi_schema_url,
        force_schema_update=force_schema_update,
    )

    welcome = f"""
    Welcome to Esi Link! Your CLI interface to the Eve Online ESI api.
    Application configuration data located at {cli_config.esi_link_config_path}
    Schema status: {cli_config.esi_link.esi_schema.download_date if cli_config.esi_link else "N/A"}
    """
    if not cli_config.silent:
        console.print(welcome)


@app.command()
def remove_config(
    ctx: typer.Context,
):
    """Remove the Esi Link configuration. A new configuration will be created on next run."""
    console = Console()
    cli_config: CliConfig = ctx.obj
    config_path = cli_config.esi_link_config_path
    if config_path is None:
        console.print("[red]Configuration path is not set in CLI context.[/red]")
        raise typer.Exit(code=1)
    if config_path.exists():
        console.print(
            f"[yellow]Removing existing configuration file at {config_path}...[/yellow]"
        )
        confirm = console.input("Press [Yy] to confirm, or any other key to cancel: ")
        if confirm.lower() != "y":
            console.print("[red]Configuration reset cancelled by user.[/red]")
            raise typer.Exit(code=0)
        try:
            config_path.unlink()
            console.print("[green]Configuration file removed.[/green]")
            console.print(
                "[yellow]Re-initialize the configuration by running `esi_link status`.[/yellow]"
            )
        except Exception as e:
            logger.error(f"Error removing configuration file at {config_path}: {e}")
            console.print(f"[red]Error removing configuration file: {e}[/red]")
            raise typer.Exit(code=1) from e
    else:
        console.print(
            f"[yellow]No existing configuration file found at {config_path}.[/yellow]"
        )
    console.print("[green]Esi Link configuration reset complete.[/green]")


@app.command()
def status(ctx: typer.Context):
    """Show the status of the Esi Link configuration."""
    console = Console()
    cli_config: CliConfig = ctx.obj
    if cli_config.esi_link_config is None:
        console.print("[red]Esi Link configuration is not initialized.[/red]")
        raise typer.Exit(code=1)
    console.print("[green]Esi Link configuration status:[/green]")
    console.print(f"  Debug: {cli_config.debug}")
    console.print(f"  Verbosity: {cli_config.verbosity}")
    console.print(f"  Silent: {cli_config.silent}")
    console.print(f"  Config Path: {cli_config.esi_link_config_path}")
    console.print(f"  Schema URL: {cli_config.esi_link_config.esi_schema_url}")
    console.print(
        f"  Schema Loaded: {cli_config.esi_link_config.esi_schema is not None}"
    )


def _init_config(
    ctx: typer.Context,
    config_path: Path,
    esi_schema_url: str | None,
    force_schema_update: bool = False,
) -> None:
    """Initialize the CLI configuration with cache and client."""
    start = perf_counter()
    console = Console()
    logger.info(f"Loading Esi Link configuration from {config_path}")
    cli_config: CliConfig = ctx.obj
    config_dirty = False
    # Load or create Esi Link configuration
    if config_path.exists():
        try:
            esi_link_config = EsiLinkConfig.load_config(file_path=config_path)
        except Exception as e:
            logger.error(
                f"Error loading Esi Link configuration from {config_path}: {e}"
            )
            raise typer.Exit(code=1) from e
    else:
        console.print(
            f"[yellow]Esi Link configuration file not found at {config_path}, creating new configuration.[/yellow]"
        )
        esi_link_config = EsiLinkConfig()
        config_dirty = True
    # Override ESI schema URL if provided, and download schema.
    if esi_schema_url is not None:
        logger.info(f"Overriding ESI schema URL to {esi_schema_url}.")
        console.print(
            f"[yellow]Overriding ESI schema URL to {esi_schema_url}.[/yellow]"
        )
        config_dirty = True
        esi_link_config.esi_schema_url = esi_schema_url
        esi_schema = _download_esi_schema(
            url=esi_link_config.esi_schema_url,
            headers={"User-Agent": USER_AGENT},
        )
        esi_link_config.esi_schema = esi_schema

    if esi_link_config.esi_schema is None or force_schema_update:
        console.print(
            f"[yellow]ESI schema not found in configuration, and/or force update is enabled, downloading from {esi_link_config.esi_schema_url}...[/yellow]"
        )
        config_dirty = True
        esi_schema = _download_esi_schema(
            url=esi_link_config.esi_schema_url,
            headers={"User-Agent": USER_AGENT},
        )
        esi_link_config.esi_schema = esi_schema

    if config_dirty:
        console.print(
            f"[yellow]Saving updated Esi Link configuration to {config_path}...[/yellow]"
        )
        try:
            esi_link_config.save_config(file_path=config_path, overwrite=True)
            console.print("[green]Configuration save complete.[/green]")
        except Exception as e:
            logger.error(f"Error saving Esi Link configuration to {config_path}: {e}")
            console.print(f"[red]Error saving configuration: {e}[/red]")
            raise typer.Exit(code=1) from e

    cli_config.esi_link_config = esi_link_config
    cli_config.esi_link = esi_link_factory(cli_config.esi_link_config)
    logger.info(f"EsiLink initialized in {perf_counter() - start:.2f} seconds.")


def _download_esi_schema(url: str, headers: dict[str, str]) -> EsiSchema:
    console = Console()
    try:
        esi_schema = download_esi_schema(
            url=url,
            headers=headers,
        )
        console.print("[green]ESI schema download complete.[/green]")
        return esi_schema
    except Exception as e:
        logger.error(f"Error downloading ESI schema: {e}")
        console.print(f"[red]Error downloading ESI schema: {e}[/red]")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
