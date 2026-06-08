"""Script to check caching and retrieving schemas and compatibility dates from the app-data database."""

import asyncio
from logging import basicConfig

from rich.console import Console

from esi_link.app_data.app_data import AppDataSqlite
from esi_link.helpers.http_client import config_async_http_client, config_http_client
from esi_link.helpers.settings_factories import app_data_db_uri_factory
from esi_link.settings import get_settings

basicConfig(level="INFO")

if __name__ == "__main__":
    settings = get_settings()
    db_uri = app_data_db_uri_factory(settings)

    async def get_cached_schemas() -> None:
        console = Console()
        app_data = AppDataSqlite(
            db_uri,
            session=config_http_client(),
            async_session=await config_async_http_client(),
        )
        async with app_data:
            console.print("Possible compatibility dates:")
            console.print(app_data.schema_cache.schema_versions())

            compatibility_date = "2025-04-01"
            cached_schema = app_data.schema_cache.get_cached_schema(compatibility_date)
            console.print(
                f"Loaded Cached schema for compatibility date {cached_schema.esi_schema.version}"
            )

            latest_cached_schema = app_data.schema_cache.get_latest_cached_schema()
            console.print(
                f"Loaded Latest Cached schema for compatibility date {latest_cached_schema.esi_schema.version}"
            )

            available_schemas = app_data.schema_cache.cached_schemas()
            console.print("Available cached schemas:")
            for schema in available_schemas:
                console.print(
                    f"- {schema.compatibility_date} fetched at {schema.timestamp_instant}"
                )

    metadata = asyncio.run(get_cached_schemas())
