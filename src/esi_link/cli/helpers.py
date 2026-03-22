"""Helper functions for the ESI Link CLI."""

from pathlib import Path
from typing import cast

import typer

from esi_link.factory import EsiLinkObjectFactory
from esi_link.models_and_protocols import EsiSchema
from esi_link.settings import EsiLinkSettings


def get_settings_from_context(ctx: typer.Context):
    """Helper function to get the ESI Link settings from the Typer context."""
    if ctx.obj is None or "esi-link-settings" not in ctx.obj:
        raise ValueError("ESI Link settings not found in context.")
    return cast(EsiLinkSettings, ctx.obj["esi-link-settings"])


def factory_from_settings(
    settings: EsiLinkSettings,
    schema: EsiSchema,
    response_handler_plugins_config: Path | None = None,
    response_group_handler_plugins_config: Path | None = None,
) -> EsiLinkObjectFactory:
    """Helper function to create an ESI Link Object Factory from settings."""
    if settings.cache_type == "json":
        cache_directory = settings.json_cache_directory
    elif settings.cache_type == "diskcache":
        cache_directory = settings.diskcache_directory
    else:
        raise ValueError(
            f"Unsupported cache type: {settings.cache_type}. Supported types are 'json' and 'diskcache'."
        )
    return EsiLinkObjectFactory(
        schema=schema,
        cache_directory=cache_directory,
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
        cache_type=settings.cache_type,
        rate_limit_max_rate=settings.connection_max_rate,
        rate_limit_time_period=settings.connection_period,
        auth_min_seconds=settings.token_refresh_threshold_seconds,
        response_group_handler_plugins_config=response_group_handler_plugins_config,
        response_handler_plugins_config=response_handler_plugins_config,
    )
