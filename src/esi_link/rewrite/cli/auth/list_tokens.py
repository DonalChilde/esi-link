"""CLI command for listing authentication tokens."""

# pyright: standard

import typer
from rich.console import Console
from rich.markdown import Markdown

from esi_link.rewrite.auth.models import CharacterToken
from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.settings_factories import (
    token_store_factory,
)

app = typer.Typer(no_args_is_help=True)


@app.command(name="list")
def list_tokens(ctx: typer.Context) -> None:
    """List all available tokens."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    token_store = token_store_factory(settings)
    with token_store:
        characters = token_store.character_tokens
        if not characters:
            console.print("[yellow]No tokens found.[/yellow]")
            raise typer.Exit(0)
        console.print("[bold]Available Tokens:[/bold]")
        markdown_table = _markdown_format_character_tokens(characters)
        console.print(Markdown(markdown_table))


def _markdown_format_character_tokens(
    character_tokens: dict[int, CharacterToken],
) -> str:
    """Format the character tokens as a markdown table."""
    if not character_tokens:
        return "No tokens found."
    table = "| Character ID | Character Name | Expires In |\n"
    table += "|--------------|----------------|------------|\n"
    for character_id, token in character_tokens.items():
        if token.expires_in < 0:
            expires_in = "Expired"
        else:
            expires_in = f"{token.expires_in} seconds"
        table += f"| {character_id} | {token.character_name} | {expires_in} |\n"
    return table
