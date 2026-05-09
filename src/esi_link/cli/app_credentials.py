"""CLI commands for managing app credentials."""

import asyncio
from pathlib import Path
from typing import Annotated, Any

import aiohttp
import typer
from rich.console import Console
from rich.json import JSON
from rich.prompt import Confirm

from esi_link.auth_factory import create_authentication_tool, create_token_tool
from esi_link.cli.helpers import get_esi_link_settings_from_context
from esi_link.esi_auth.auth_store import AuthStoreDisk, AuthStoreRoot, init_auth_store
from esi_link.esi_auth.models import (
    CharacterToken,
    EsiAppCredentialsRoot,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def show_raw(ctx: typer.Context):
    """Show the stored app credentials."""
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    store_text = (
        settings.auth_credentials_file.read_text()
        if settings.auth_credentials_file.exists()
        else None
    )
    if store_text is None:
        console.print(
            f"[red]No app credentials found at {settings.auth_credentials_file}.[/red]"
        )
        raise typer.Exit(code=1)
    store = AuthStoreRoot.model_validate_json(store_text).root
    console.print(JSON.from_data(store))


@app.command()
def init_store(
    ctx: typer.Context,
    file_path: Annotated[
        Path, typer.Argument(help="Path to the app credential JSON file to add.")
    ],
):
    """Add a new app credential.

    Expects a JSON file in the format of `EsiAppCredentials`. The file is read
    and validated, and then stored in the app.
    """
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    if settings.auth_credentials_file.exists():
        console.print(
            f"[red]Warning: App credentials file already exists at {settings.auth_credentials_file}. "
            "It must be removed first.[/red]"
        )
        raise typer.Exit(code=1)
    if not file_path.is_file():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(code=1)
    try:
        credential = EsiAppCredentialsRoot.model_validate_json(
            file_path.read_text()
        ).root
    except Exception as e:
        console.print(f"[red]Error reading credential file: {e}[/red]")
        raise e

    settings.auth_credentials_file.parent.mkdir(parents=True, exist_ok=True)
    init_auth_store(store_path=settings.auth_credentials_file, credentials=credential)
    console.print(f"App credentials added to {settings.auth_credentials_file}")


@app.command()
def remove_store(ctx: typer.Context):
    """Remove the stored app credentialsand associated token files."""
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    if not settings.auth_credentials_file.exists():
        console.print(
            f"[red]App credentials file not found at {settings.auth_credentials_file}[/red]"
        )
        raise typer.Exit(code=1)
    is_confirmed = Confirm.ask(
        f"Are you sure you want to remove the app credentials at {settings.auth_credentials_file}?\n"
        f"This will also remove any associated tokens."
    )
    if not is_confirmed:
        console.print("Aborting app credential removal.")
        raise typer.Exit(code=1)
    try:
        settings.auth_credentials_file.unlink()
        console.print(f"App credentials removed from {settings.auth_credentials_file}")
    except Exception as e:
        console.print(f"[red]Error removing app credentials: {e}[/red]")
        raise e


@app.command()
def add(
    ctx: typer.Context,
    test_token: Annotated[
        bool,
        typer.Option(
            "-t",
            "--test-token",
            help="Make a request to the EVE ESI to prove the token is working",
        ),
    ] = False,
):
    """Add a new CharacterToken."""
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    token_tool = create_token_tool(settings)
    auth_tool = create_authentication_tool(settings)
    auth_store = AuthStoreDisk(settings.auth_credentials_file, token_tool=token_tool)
    request_params = auth_tool.generate_request_params()

    console.print(f"Navigate to the following URL to authenticate:\n")
    console.print(f"[link={request_params.redirect_url}]......Click ME......[/link]\n")
    console.print(
        f"Or copy and paste the URL into your browser if your terminal does not support clickable links.\n"
    )
    console.print(f"{request_params.redirect_url}\n")

    console.print(f"Listening on {auth_tool.callback_url} for callback...\n")
    console.print(
        "The local server can take a second to start. If the link gives an error, try reloading the page after a moment.\n"
    )

    # Launch a web server to listen for the callback and get the authorization code.
    # then get and validate the token to make a CharacterToken.
    async def code_flow() -> CharacterToken:
        auth_code = await auth_tool.request_authentication_code(
            auth_params=request_params
        )
        async with aiohttp.ClientSession() as session:
            oauth_token = await token_tool.request_new_token(
                client_id=auth_tool.client_id,
                authorization_code=auth_code,
                code_verifier=request_params.code_verifier,
                client_session=session,
            )
            character_token = token_tool.character_token_from_oauth_token(oauth_token)
            async with auth_store as store:
                store.add_token(character_token)
        return character_token

    character_token = asyncio.run(code_flow())
    console.print(f"Character token for {character_token.character_name} added.\n")
    if test_token:
        console.print(f"Testing token by fetching character attributes from ESI...\n")
        try:
            attributes = asyncio.run(
                get_character_attributes(
                    character_token, user_agent=settings.user_agent
                )
            )
            console.print(f"Token is valid. Character attributes:")
            console.print(JSON.from_data(attributes))
        except Exception as e:
            console.print(f"[red]Error testing token: {e}[/red]\n")
            raise typer.Exit(code=1) from e


@app.command(name="list")
def list_tokens(
    ctx: typer.Context,
):
    """List all CharacterTokens."""
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    token_tool = create_token_tool(settings)
    auth_store = AuthStoreDisk(settings.auth_credentials_file, token_tool=token_tool)

    async def list_tokens() -> list[CharacterToken]:
        """List all CharacterTokens in the auth store without refreshing them."""
        async with auth_store as store:
            tokens = await store.get_tokens(min_seconds=0)
        result = [x for x in tokens.values()]
        return result

    tokens = asyncio.run(list_tokens())
    for token in tokens:
        console.print(
            f"- {token.character_name} (ID: {token.character_id}), Expires in: {token.expires_in} seconds\n"
        )


@app.command()
def remove(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(help="ID of the character token to remove.")
    ],
):
    """Remove and revoke a CharacterToken by character ID."""
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    token_tool = create_token_tool(settings)
    auth_store = AuthStoreDisk(settings.auth_credentials_file, token_tool=token_tool)

    async def remove_token() -> None:
        async with auth_store as store:
            await store.remove_token(character_id)

    try:
        asyncio.run(remove_token())
        console.print(f"Token for character ID {character_id} removed and revoked.\n")
    except KeyError:
        console.print(f"[red]No token found for character ID {character_id}.[/red]\n")
        raise typer.Exit(code=1) from KeyError
    except Exception as e:
        console.print(f"[red]Error removing token: {e}[/red]\n")
        raise e


@app.command()
def refresh(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(help="ID of the character token to refresh.")
    ],
    min_seconds: Annotated[
        int,
        typer.Option(
            "-m",
            "--min-seconds",
            help="Minimum seconds to expiration to trigger refresh",
        ),
    ] = 300,
):
    """Refresh a CharacterToken by character ID."""
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    token_tool = create_token_tool(settings)
    auth_store = AuthStoreDisk(settings.auth_credentials_file, token_tool=token_tool)

    async def refresh_token() -> CharacterToken:
        async with auth_store as store:
            token = await store.get_token(character_id, min_seconds=min_seconds)
        return token

    try:
        token = asyncio.run(refresh_token())
        console.print(
            f"Token for {token.character_name}-{token.character_id} is valid, expires in {token.expires_in} seconds.\n"
        )
    except KeyError:
        console.print(f"[red]No token found for character ID {character_id}.[/red]\n")
        raise typer.Exit(code=1) from KeyError
    except Exception as e:
        console.print(f"[red]Error refreshing token: {e}[/red]\n")
        raise e


@app.command()
def refresh_all(
    ctx: typer.Context,
    min_seconds: Annotated[
        int,
        typer.Option(
            "-m",
            "--min-seconds",
            help="Minimum seconds to expiration to trigger refresh",
            show_default=True,
        ),
    ] = 300,
):
    """Refresh all CharacterTokens."""
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    token_tool = create_token_tool(settings)
    auth_store = AuthStoreDisk(settings.auth_credentials_file, token_tool=token_tool)

    async def refresh_all_tokens() -> dict[int, CharacterToken]:
        async with auth_store as store:
            tokens = await store.get_tokens(min_seconds=min_seconds)
        return tokens

    try:
        tokens = asyncio.run(refresh_all_tokens())
        if not tokens:
            console.print("No tokens found.\n")
            return

        console.print(f"Refreshed {len(tokens)} token(s):\n")
        for token in tokens.values():
            console.print(
                f"- {token.character_name} (ID: {token.character_id}), Expires in: {token.expires_in} seconds"
            )
    except Exception as e:
        console.print(f"[red]Error refreshing tokens: {e}[/red]\n")
        raise e


async def get_character_attributes(
    character_token: CharacterToken, user_agent: str
) -> dict[str, Any]:
    """Get character attributes from ESI using the token.

    Demonstrates use of the AuthProvider and CharacterTokenManager to get a valid token
    and make an authenticated request to ESI.
    """
    async with aiohttp.ClientSession() as session:
        headers: dict[str, str] = {
            "User-Agent": user_agent,
        }
        headers.update(character_token.auth_headers)
        url = f"https://esi.evetech.net/characters/{character_token.character_id}/attributes"
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(
                    f"Failed to get character attributes: {response.status} {response.reason}"
                )
            data = await response.json()
            return data
