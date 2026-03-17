"""Helper classes and functions for the ESI Auth CLI."""

import asyncio

import typer
from rich.console import Console

from esi_link.esi_auth.authenticator import Authenticator
from esi_link.esi_auth.credentials_provider import CredentialsProvider
from esi_link.esi_auth.models import CachedMetadata, EveAppCredentials
from esi_link.esi_auth.oauth_metadata import MetadataProvider
from esi_link.v3.settings import EsiLinkSettings


def load_credentials(settings: EsiLinkSettings, console: Console) -> EveAppCredentials:
    """Load the app credentials from the settings file."""
    provider = CredentialsProvider(credentials_file=settings.app_credentials_file)
    try:
        credentials = provider.get_credentials()
    except FileNotFoundError as e:
        console.print(
            f"[red]App credentials file not found at {settings.app_credentials_file}[/red]"
        )
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Error reading app credentials: {e}[/red]")
        raise typer.Exit(code=1) from e
    return credentials


def load_cached_oauth_metadata(
    settings: EsiLinkSettings, console: Console
) -> CachedMetadata:
    """Load the cached OAuth metadata, refreshing it if it's expired."""
    metadata_provider = MetadataProvider(
        cache_file=settings.cached_oauth_metadata_file,
        metadata_url=settings.oauth_metadata_url,
    )
    try:
        cached_metadata = asyncio.run(
            metadata_provider.get_cached_metadata(
                max_age=settings.cached_metadata_max_age
            )
        )
    except Exception as e:
        console.print(f"[red]Error loading OAuth metadata: {e}[/red]")
        raise typer.Exit(code=1) from e
    return cached_metadata


def get_authenticator(settings: EsiLinkSettings, console: Console) -> Authenticator:
    """Create an Authenticator instance using the app credentials and cached OAuth metadata."""
    creds = load_credentials(settings, console)
    oauth_metadata = load_cached_oauth_metadata(settings, console)
    authenticator = Authenticator.from_dict(
        client_id=creds.clientId,
        scopes=creds.scopes,
        callback_url=creds.callbackUrl,
        config_dict=oauth_metadata["metadata"],
    )
    return authenticator
