"""Helper classes and functions for the ESI Auth CLI."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from esi_link.esi_auth.models import CachedMetadata, EveAppCredentials
from esi_link.esi_auth.oauth_metadata import oauth_metadata_cache


def load_credentials(file_path: Path, console: Console) -> EveAppCredentials:
    """Load the app credentials from the settings file."""
    try:
        credentials = EveAppCredentials.model_validate_json(file_path.read_text())
    except FileNotFoundError as e:
        console.print(f"[red]App credentials file not found at {file_path}[/red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Error reading app credentials: {e}[/red]")
        raise typer.Exit(code=1) from e
    return credentials


def load_cached_oauth_metadata(
    file_path: Path, max_age: int, url: str, console: Console
) -> CachedMetadata:
    """Load the cached OAuth metadata, refreshing it if it's expired."""
    try:
        cached_metadata = asyncio.run(
            oauth_metadata_cache(file_path=file_path, max_age=max_age, url=url)
        )
    except Exception as e:
        console.print(f"[red]Error loading OAuth metadata: {e}[/red]")
        raise typer.Exit(code=1) from e
    return cached_metadata
