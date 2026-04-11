"""Commands for showing Esi Link configuration information."""

import typer
from rich.console import Console
from rich.text import Text

from esi_link import __app_name__, __version__
from esi_link.cli import STYLE_INFO
from esi_link.cli.helpers import get_esi_link_settings_from_context

app = typer.Typer(no_args_is_help=True)


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
    settings = get_esi_link_settings_from_context(ctx)
    console.print(settings)
