"""Helpers for the ESI schema manager."""

from typing import Any

from whenever import Instant

from esi_link.v3 import USER_AGENT
from esi_link.v3.helpers.aiohttp.download_files import download_json
from esi_link.v3.models_and_protocols import SchemaDownload
from esi_link.v3.schema.errors import InvalidSchemaError, SchemaManagerError
from esi_link.v3.settings import ESI_SCHEMA_CHANGELOG_URL, ESI_SCHEMA_URL


async def download_schema(
    compatibility_date: str,
    url: str = ESI_SCHEMA_URL,
) -> SchemaDownload:
    """Download the ESI schema from the specified URL.

    Args:
        url (str): The URL to download the ESI schema from. Defaults to ESI_SCHEMA_URL.
        compatibility_date (str): The compatibility date to use for the ESI schema download.

    Returns:
        SchemaDownload: A SchemaDownload object containing the downloaded schema and its download date.

    Raises:
        InvalidSchemaError: If the downloaded schema is missing required OpenAPI fields.
        SchemaManagerError: If there is an error downloading the ESI schema.
    """
    try:
        schema, _ = await download_json(
            url=url,
            headers={"User-Agent": USER_AGENT},
            params={"compatibility_date": compatibility_date},
        )
        if not all(k in schema for k in ("openapi", "info", "paths")):
            raise InvalidSchemaError(
                "Downloaded schema is missing required OpenAPI fields"
            )
        download_date = Instant.now()
        return SchemaDownload(raw_schema=schema, download_date=download_date)
    except Exception as e:
        raise SchemaManagerError(
            f"Error downloading ESI schema from {url}: {str(e)}"
        ) from e


async def download_schema_changelog(
    url: str = ESI_SCHEMA_CHANGELOG_URL,
) -> dict[str, Any]:
    """Download the ESI schema changelog from the specified URL.

    Args:
        url (str): The URL to download the ESI schema changelog from. Defaults to ESI_SCHEMA_CHANGELOG_URL.

    Returns:
        dict[str, Any]: The downloaded ESI schema changelog.

    Raises:
        SchemaManagerError: If there is an error downloading the ESI schema changelog.
    """
    try:
        changelog, _ = await download_json(
            url=url,
            headers={"User-Agent": USER_AGENT},
        )
        return changelog
    except Exception as e:
        raise SchemaManagerError(
            f"Error downloading ESI schema changelog from {url}: {str(e)}"
        ) from e
