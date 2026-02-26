"""Main entry point for the Esi Link CLI using Typer."""

import logging

import typer
from rich.console import Console
from rich.text import Text

from esi_link.cli import STYLE_INFO
from esi_link.v2 import __app_name__, __version__
from esi_link.v2.cli.cache import app as cache_app
from esi_link.v2.cli.esi_schema import app as esi_schema_app
from esi_link.v2.logging_config import setup_logging
from esi_link.v2.settings import get_settings

logger = logging.getLogger(__name__)
app = typer.Typer(no_args_is_help=True)
app.add_typer(
    esi_schema_app, name="schema", help="ESI schema information and management."
)
app.add_typer(cache_app, name="cache", help="ESI cache management commands.")


@app.callback(invoke_without_command=True)
def default_options(ctx: typer.Context):
    """Esi Link Command Line Interface.

    Insert pithy saying here
    """
    settings = get_settings()
    setup_logging(log_dir=settings.log_dir)
    logger.info(f"Starting {__app_name__} v{__version__}")


@app.command()
def version():
    """Show the version of Esi Link."""
    console = Console()
    console.print(Text(f"{__app_name__} v{__version__}"), style=STYLE_INFO)


@app.command()
def status(ctx: typer.Context):
    """Show the status of the Esi Link configuration."""
    console = Console()
    console.rule(Text("esi-link Cli Configuration Information", style=STYLE_INFO))
    settings = get_settings()
    console.print(settings)
