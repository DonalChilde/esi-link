"""Script to print the current OAuth metadata from the app-data database."""

import asyncio

from rich.console import Console

from esi_link.app_data.app_data import AppDataSqlite
from esi_link.auth.oauth_metadata_sqlite import OAuthMetadataTimestamped
from esi_link.helpers.http_client import config_async_http_client, config_http_client
from esi_link.helpers.settings_factories import app_data_db_uri_factory
from esi_link.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    db_uri = app_data_db_uri_factory(settings)

    async def get_oauth_metadata() -> OAuthMetadataTimestamped:
        app_data = AppDataSqlite(
            db_uri,
            session=config_http_client(),
            async_session=await config_async_http_client(),
        )
        async with app_data:
            return app_data.oauth_metadata

    metadata = asyncio.run(get_oauth_metadata())
    console = Console()
    console.print(metadata)
