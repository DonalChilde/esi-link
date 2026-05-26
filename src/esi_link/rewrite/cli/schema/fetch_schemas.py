"""CLI commands for fetching ESI schemas."""

# pyright: standard
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.http_client import config_http_client
from esi_link.rewrite.helpers.settings_factories import schema_cache_factory

app = typer.Typer(no_args_is_help=True)


@app.command()
def fetch(
    ctx: typer.Context,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "-c",
            "--compatibility-date",
            help="The compatibility date for the schema to fetch. If not provided, the "
            "latest valid compatibility date will be used.",
        ),
    ] = None,
) -> None:
    """Fetch and cache the ESI schema for a given compatibility date."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    schema_cache = schema_cache_factory(settings)
    session = config_http_client()
    with session:
        valid_dates = schema_cache.valid_compatibility_dates(session)
        if not valid_dates:
            console.print("No valid compatibility dates found.")
            raise typer.Exit(0)
        if compatibility_date is not None:
            if compatibility_date not in valid_dates["compatibility_dates"]:
                console.print(
                    f"[red]Compatibility date {compatibility_date} is not valid.[/red]"
                )
                console.print("Valid compatibility dates are:")
                for date in valid_dates["compatibility_dates"]:
                    console.print(f"- {date}")
                raise typer.Exit(1)
            console.print(
                f"Fetching schema for compatibility date {compatibility_date}..."
            )
        else:
            latest_date = max(valid_dates["compatibility_dates"])
            console.print(f"Fetching latest valid compatibility date {latest_date}...")
            compatibility_date = latest_date
        try:
            cached_schema = schema_cache.fetch_and_cache_schema(
                session, compatibility_date
            )
            console.print(
                f"Successfully fetched schema for compatibility date {cached_schema.esi_schema.version}."
            )
        except Exception as e:
            console.print(
                f"[red]Failed to fetch schema for compatibility date {compatibility_date}: {e}[/red]"
            )
            raise e
