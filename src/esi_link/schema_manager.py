"""Module for managing ESI schemas, including downloading, transforming, and storing schemas."""

from typing import Any

from whenever import Instant

from esi_link.esi_schema import (
    add_schema_to_store,
    download_schema,
    load_schema_store,
)
from esi_link.models import (
    IndexedEsiSchema,
    IndexedSchemaStore,
    SchemaDownload,
    SchemaManagerProtocol,
)
from esi_link.settings import EsiLinkSettings


class SchemaManager(SchemaManagerProtocol):
    def __init__(self, settings: EsiLinkSettings):
        """Initialize the SchemaManager instance."""
        self._settings = settings
        self._schema_store: IndexedSchemaStore = load_schema_store(
            settings=self._settings
        )

    def get_schema_for_date(self, compatibility_date: str) -> IndexedEsiSchema:
        """Get the ESI schema corresponding to the given compatibility date."""
        schema = self._schema_store.schemas.get(compatibility_date)
        if not schema:
            raise ValueError(
                f"No schema found for compatibility date {compatibility_date}"
            )
        return schema

    def get_latest_schema(self) -> IndexedEsiSchema:
        """Get the latest ESI schema available in the schema store."""
        schema = self._schema_store.latest_schema()
        if not schema:
            raise ValueError("No schemas found in the schema store")
        return schema

    def available_schemas(self) -> list[str]:
        """Return a list of available compatibility dates for schemas in the store."""
        return list(self._schema_store.schemas.keys())

    def add_schema(self, schema: IndexedEsiSchema) -> None:
        """Add a new schema to the schema store."""
        add_schema_to_store(settings=self._settings, indexed_schema=schema)
        self._schema_store = load_schema_store(settings=self._settings)

    def transform_schema(
        self, raw_schema: dict[str, Any], download_date: Instant
    ) -> IndexedEsiSchema:
        """Transform a raw OpenAPI schema into an IndexedEsiSchema."""
        schema = IndexedEsiSchema.from_raw_schema(
            raw_schema=raw_schema, download_date=download_date
        )
        return schema

    def download_schema(self, compatibility_date: str | None = None) -> SchemaDownload:
        """Download the ESI schema for the given compatibility date."""
        schema_download = download_schema(
            settings=self._settings, compatibility_date=compatibility_date
        )
        return schema_download
