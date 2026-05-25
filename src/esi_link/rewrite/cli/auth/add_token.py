"""CLI command for adding a token for a character."""

# pyright: standard
import webbrowser
from typing import Annotated

import typer
from rich.console import Console

from esi_link.rewrite.auth.helpers.request_authentication_code import (
    generate_request_params,
    start_web_server_and_listen_for_code,
)
from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.http_client import config_http_client
from esi_link.rewrite.helpers.settings_factories import (
    metadata_cache_factory,
    token_store_factory,
    token_tool_factory,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def add(
    ctx: typer.Context,
    character_id: Annotated[
        int,
        typer.Argument(
            help="The character ID to add a token for.",
        ),
    ],
    browser_auto_open: Annotated[
        bool, typer.Option(help="Whether to automatically open the browser.")
    ] = True,
    server_timeout: Annotated[
        int, typer.Option(help="Seconds to wait for authentication code.")
    ] = 120,
) -> None:
    """Add a token for a character."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    token_tool = token_tool_factory(settings)
    token_store = token_store_factory(settings)
    oauth_metadata = metadata_cache_factory(settings).metadata
    with token_store:
        if character_id in token_store.available_character_ids:
            console.print(
                f"[yellow]A token for character ID {character_id} already exists.[/yellow]"
            )
            raise typer.Exit(1)
        credentials = token_store.credentials
        request_params = generate_request_params(
            client_id=credentials.clientId,
            callback_url=credentials.callbackUrl,
            authorization_endpoint=oauth_metadata.authorization_endpoint,
            scopes=credentials.scopes,
        )
        if browser_auto_open:
            opened = webbrowser.open(request_params.redirect_url)
            if opened:
                console.print("Opened browser for authorization.")
            else:
                console.print(
                    "Could not automatically open browser. Visit this URL to continue:"
                )
                console.print(request_params.redirect_url)
        else:
            console.print("Visit this URL to continue:")
            console.print(request_params.redirect_url)
        authorization_code = start_web_server_and_listen_for_code(
            redirect_url=credentials.callbackUrl,
            expected_state=request_params.state,
            timeout_seconds=server_timeout,
        )
        if not authorization_code:
            console.print(
                f"[red]Did not receive authentication code within {server_timeout} seconds.[/red]"
            )
            raise typer.Exit(1)
        console.print("Received authentication code, exchanging for token...")
        session = config_http_client()
        oauth_token = token_tool.request_new_token(
            client_id=credentials.clientId,
            authorization_code=authorization_code,
            code_verifier=request_params.code_verifier,
            session=session,
        )
        character_token = token_tool.create_character_token(oauth_token)
        if character_token.character_id != character_id:
            console.print(
                f"[red]Received token for character ID {character_token.character_id}, but expected {character_id}.[/red]"
            )
            raise typer.Exit(1)
        token_store.add_character_token(character_token)
    console.print(
        f"[green]Successfully added token for character ID {character_id}.[/green]"
    )
