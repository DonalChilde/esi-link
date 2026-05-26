"""CLI commands for listing valid compatibility dates for ESI schemas."""

import typer
from rich.console import Console
from rich.markdown import Markdown

from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.http_client import config_http_client
from esi_link.rewrite.helpers.settings_factories import schema_cache_factory

app = typer.Typer(no_args_is_help=True)


@app.command(name="valid-dates")
def valid_compatibility_dates(ctx: typer.Context) -> None:
    """List all valid compatibility dates for ESI schemas."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    schema_cache = schema_cache_factory(settings)
    session = config_http_client()
    with session:
        compatibility_dates = schema_cache.valid_compatibility_dates(session)
    if not compatibility_dates:
        console.print("No valid compatibility dates found.")
        raise typer.Exit(0)
    console.print("Valid Compatibility Dates:")
    for date in compatibility_dates["compatibility_dates"]:
        console.print(f"- {date}")
