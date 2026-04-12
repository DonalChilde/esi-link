"""Commands for managing OAuth settings, including fetching from the ESI auth server and displaying the current settings."""

import typer
from rich.console import Console
from rich.json import JSON
from whenever import Instant

from esi_link.cli.helpers import get_esi_link_settings_from_context
from esi_link.esi_auth.cli.helpers import load_cached_oauth_metadata

app = typer.Typer(no_args_is_help=True)


@app.command()
def show(ctx: typer.Context):
    """Show the current ESI Auth settings.

    Loads the cached OAuth metadata and displays it, along with the time until it expires.
    If the metadata is expired, it will be refreshed automatically and the new metadata
    will be displayed.
    """
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    cached_metadata = load_cached_oauth_metadata(settings, console)
    expires_in = (
        cached_metadata["fetched_at"]
        + settings.cached_metadata_max_age
        - Instant.now().timestamp()
    )
    console.print(f"Cached metadata expires in {expires_in:.0f} seconds.")
    console.print(JSON.from_data(cached_metadata, indent=2))
