"""Helper functions for the ESI Link CLI."""

from pathlib import Path
from typing import cast

import typer

from esi_link import EsiLink
from esi_link.models_and_protocols import EsiSchema
from esi_link.schema.schema_manager import SchemaManager
from esi_link.settings import EsiLinkSettings


def get_settings_from_context(ctx: typer.Context) -> EsiLinkSettings:
    """Helper function to get the ESI Link settings from the Typer context."""
    if ctx.obj is None or "esi-link-settings" not in ctx.obj:
        raise ValueError("ESI Link settings not found in context.")
    return cast(EsiLinkSettings, ctx.obj["esi-link-settings"])


# def factory_from_settings(
#     settings: EsiLinkSettings,
#     schema: EsiSchema,
#     response_handler_plugins_config: Path | None = None,
#     response_group_handler_plugins_config: Path | None = None,
# ) -> EsiLinkObjectFactory:
#     """Helper function to create an ESI Link Object Factory from settings."""
#     if settings.cache_type == "json":
#         cache_directory = settings.json_cache_directory
#     elif settings.cache_type == "diskcache":
#         cache_directory = settings.diskcache_directory
#     else:
#         raise ValueError(
#             f"Unsupported cache type: {settings.cache_type}. Supported types are 'json' and 'diskcache'."
#         )
#     return EsiLinkObjectFactory(
#         schema=schema,
#         cache_directory=cache_directory,
#         credentials_file=settings.app_credentials_file,
#         tokens_dir=settings.tokens_dir,
#         cache_type=settings.cache_type,
#         rate_limit_max_rate=settings.connection_max_rate,
#         rate_limit_time_period=settings.connection_period,
#         auth_min_seconds=settings.token_refresh_threshold_seconds,
#         response_group_handler_plugins_config=response_group_handler_plugins_config,
#         response_handler_plugins_config=response_handler_plugins_config,
#     )


def get_executor_from_settings_and_schema(
    settings: EsiLinkSettings,
    schema: EsiSchema | None = None,
    response_handler_plugins_config: Path | None = None,
    response_group_handler_plugins_config: Path | None = None,
) -> EsiLink:
    """Helper function to create an ESI Link Object Factory and get the RequestGroupExecutor from it."""
    if schema is None:
        schema_manager = SchemaManager(schema_directory=settings.schema_store_directory)
        stored_schema = schema_manager.get_latest_schema()
        schema = stored_schema.esi_schema

    esi_link_executor = EsiLink(
        schema=schema,
        cache_type=settings.cache_type,
        cache_directory=settings.cache_directory,
        credentials_file=settings.auth_credentials_file,
        tokens_dir=settings.auth_tokens_directory,
        rate_limit_max_rate=settings.rate_limit_connection_max_rate,
        rate_limit_time_period=settings.rate_limit_connection_period,
        auth_min_seconds=settings.auth_token_refresh_threshold_seconds,
        response_group_handler_plugins_config=response_group_handler_plugins_config,
        response_handler_plugins_config=response_handler_plugins_config,
    )
    return esi_link_executor
