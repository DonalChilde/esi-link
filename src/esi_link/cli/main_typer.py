"""Command-line interface."""

import logging
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from esi_link import DEFAULT_APP_DIR, __app_name__, __version__
from esi_link.cli import STYLE_INFO
from esi_link.cli.esi_request import app as esi_request_app
from esi_link.cli.esi_schema import app as esi_schema_app
from esi_link.cli.helpers import ensure_env_example
from esi_link.cli.models import CliConfig
from esi_link.ensure_esi_schema import ensure_esi_schema
from esi_link.esi_link_factory import esi_link_factory
from esi_link.logging_config import setup_logging
from esi_link.settings import get_settings

logger = logging.getLogger(__name__)

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
    settings = get_settings()
    setup_logging(log_dir=settings.log_dir)
    console = Console()
    cli_config = CliConfig(
        debug=debug, verbosity=verbosity, silent=silent, settings=settings
    )
    ctx.obj = cli_config

    # Complete the initialization of the configuration
    _init_config(
        ctx,
        force_schema_update=force_schema_update,
    )

    welcome = f"""
    Welcome to Esi Link! Your CLI interface to the Eve Online ESI api.
    Application configuration data located at {cli_config.settings.app_dir}
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
    config_file_path = cli_config.settings.config_file
    if config_file_path.exists():
        console.print(
            f"[yellow]Removing existing configuration file at {config_file_path}...[/yellow]"
        )
        confirm = console.input("Press [Yy] to confirm, or any other key to cancel: ")
        if confirm.lower() != "y":
            console.print("[red]Configuration reset cancelled by user.[/red]")
            raise typer.Exit(code=0)
        try:
            config_file_path.unlink()
            console.print("[green]Configuration file removed.[/green]")
            console.print(
                "[yellow]Re-initialize the configuration by running `esi_link status`.[/yellow]"
            )
        except Exception as e:
            logger.error(
                f"Error removing configuration file at {config_file_path}: {e}"
            )
            console.print(f"[red]Error removing configuration file: {e}[/red]")
            raise typer.Exit(code=1) from e
    else:
        console.print(
            f"[yellow]No existing configuration file found at {config_file_path}.[/yellow]"
        )
    console.print("[green]Esi Link configuration reset complete.[/green]")


@app.command()
def status(ctx: typer.Context):
    """Show the status of the Esi Link configuration."""
    console = Console()
    console.rule(Text("esi-link Cli Configuration Information", style=STYLE_INFO))
    cli_config: CliConfig = ctx.obj
    console.print(cli_config)


@app.command()
def version(ctx: typer.Context):
    """Display version information."""
    console = Console()
    console.rule(Text("esi-link Version Information", style=STYLE_INFO))
    console.print(f"{__app_name__} version {__version__}")
    console.print(ctx.obj)


@app.command()
def example_env(
    file_path: Annotated[
        Path,
        typer.Argument(
            help="Path to create the example .env file.",
        ),
    ],
):
    """Create an example .env file for esi-link configuration."""
    console = Console()
    exists = ensure_env_example(file_path=file_path)
    if exists:
        console.print(
            f"[bold yellow]File already exists at {file_path}. No changes made.[/bold yellow]"
        )
    else:
        console.print(
            f"[bold green]Example .env file created at {file_path}.[/bold green]"
        )
        console.print(
            "[bold green]You can edit this file to configure your settings before using esi-link.[/bold green]"
        )


def _init_config(
    ctx: typer.Context,
    force_schema_update: bool = False,
) -> None:
    """Initialize the CLI configuration with cache and client."""
    start = perf_counter()
    console = Console()
    cli_config: CliConfig = ctx.obj
    settings = cli_config.settings

    try:
        esi_schema = ensure_esi_schema(
            esi_schema_path=settings.esi_schema_path,
            esi_schema_url=settings.esi_schema_url,
            force_update=force_schema_update,
        )
        cli_config.esi_schema = esi_schema
    except Exception as e:
        logger.error(f"Error ensuring ESI schema: {e}")
        console.print(f"[red]Error ensuring ESI schema: {e}[/red]")
        raise typer.Exit(code=1) from e

    cli_config.esi_link = esi_link_factory(settings=settings, esi_schema=esi_schema)
    logger.info(f"EsiLink initialized in {perf_counter() - start:.2f} seconds.")


if __name__ == "__main__":
    app()
