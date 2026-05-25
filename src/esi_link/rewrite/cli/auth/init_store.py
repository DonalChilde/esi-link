"""Module for the `init-store` command, which initializes the authentication store."""

# pyright: standard
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from esi_link.rewrite.auth.models import EsiAppCredentialsRoot
from esi_link.rewrite.auth.token_store import TokenStore
from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.settings_factories import (
    token_tool_factory,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def init_store(
    ctx: typer.Context,
    credentials_file: Annotated[
        Path,
        typer.Argument(
            help="Path to the credentials file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
) -> None:
    """Initialize the authentication store."""
    console = Console()
    console.print("[blue]Initializing authentication store...[/blue]")

    settings = get_esi_link_settings_from_context(ctx)
    token_tool = token_tool_factory(settings)

    console.print(f"[blue]Loading credentials from {credentials_file}...[/blue]")
    credentials = EsiAppCredentialsRoot.model_validate_json(
        credentials_file.read_text()
    ).root
    console.print("[green]Credentials loaded successfully.[/green]")

    console.print(
        f"[blue]Initializing token store at {settings.token_store_path}...[/blue]"
    )
    token_store = TokenStore.from_credentials(
        store_path=settings.token_store_path,
        credentials=credentials,
        token_tool=token_tool,
    )
    console.print("[green]Authentication store initialized successfully.[/green]")
