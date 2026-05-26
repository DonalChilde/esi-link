"""Module for caching ESI schemas on disk and in memory, with support for expiration based on a TTL."""

from dataclasses import dataclass
from pathlib import Path

from httpx2 import Client
from pydantic import RootModel
from whenever import Instant

from esi_link.rewrite.schema.models import EsiSchema
from esi_link.rewrite.schema.schema_tool import (
    SchemaTool,
)


@dataclass(slots=True, kw_only=True, frozen=True)
class CachedSchemaPath:
    """Represents a cached ESI schema file path, including the compatibility date and timestamp."""

    compatibility_date: str
    timestamp: int
    file_path: Path

    def is_expired(self, ttl: int) -> bool:
        """Check if the cached schema file is expired based on the provided TTL."""
        return Instant.now().timestamp() - self.timestamp > ttl


@dataclass(slots=True, kw_only=True, frozen=True)
class CachedSchema:
    """Represents a cached ESI schema, including the raw schema and the date it was downloaded."""

    esi_schema: EsiSchema
    timestamp: int
    """Seconds since the Unix epoch when the schema was fetched."""

    def is_expired(self, ttl: int) -> bool:
        """Check if the cached schema has expired based on the provided TTL."""
        return Instant.now().timestamp() - self.timestamp > ttl


CachedSchemaRoot = RootModel[CachedSchema]


class SchemaCache:
    def __init__(self, cache_directory: Path, schema_ttl: int = 2_592_000):
        """Initialize the SchemaCache.

        ttl of 2,592,000 seconds is 30 days, which is a reasonable default for caching
        ESI schemas, as they are not updated frequently, and this allows for some leeway
        in case of temporary issues with fetching the schema.
        """
        self._cache_directory = cache_directory
        self._schema_tool = SchemaTool()
        self._schema_ttl = schema_ttl
        # Cache of schemas, keyed by compatibility date, with the value being the CachedSchema instance.
        self._cached_schemas: dict[str, CachedSchema] = {}

    def _schema_files(self) -> list[Path]:
        """Return a list of schema files in the cache directory."""
        if not self._cache_directory.exists():
            return []
        return list(self._cache_directory.glob("*_esi-schema.json"))

    def _parse_schema_file_name(self, file_name: str) -> tuple[str, int] | None:
        """Parse the schema file name to extract the compatibility date and timestamp.

        The expected file name format is <compatibility_date>_<timestamp>_esi-schema.json.
        """
        if not file_name.endswith("_esi-schema.json"):
            return None
        parts = file_name[: -len("_esi-schema.json")].split("_")
        if len(parts) != 2:
            return None
        compatibility_date, timestamp_str = parts
        try:
            timestamp = int(timestamp_str)
            return compatibility_date, timestamp
        except ValueError:
            return None

    def _cached_schema_paths(self) -> dict[str, CachedSchemaPath]:
        """Return a mapping of compatibility date to the latest schema file path and timestamp."""
        schema_files = self._schema_files()
        cached_schemas: dict[str, CachedSchemaPath] = {}
        for schema_file in schema_files:
            parsed = self._parse_schema_file_name(schema_file.name)
            if parsed is None:
                continue
            compatibility_date, timestamp = parsed
            cached_schemas[compatibility_date] = CachedSchemaPath(
                compatibility_date=compatibility_date,
                timestamp=timestamp,
                file_path=schema_file,
            )
        return cached_schemas

    def _fetch_and_cache_schema(
        self, session: Client, compatibility_date: str
    ) -> CachedSchema:
        """Fetch the schema for the given compatibility date, cache it, and return the CachedSchema instance."""
        timestamped_schema = self._schema_tool.fetch_schema(session, compatibility_date)
        resolved_tss = self._schema_tool.resolve_schema(timestamped_schema)
        esi_schema = EsiSchema(dereferenced_schema=resolved_tss.schema)
        cached_schema = CachedSchema(
            esi_schema=esi_schema, timestamp=timestamped_schema.fetch_timestamp
        )
        # Cache the schema in memory
        self._cached_schemas[compatibility_date] = cached_schema
        # Cache the schema on disk
        self._cache_directory.mkdir(parents=True, exist_ok=True)
        cache_file_name = f"{esi_schema.compatibility_date}_{timestamped_schema.fetch_timestamp}_esi-schema.json"
        cache_file_path = self._cache_directory / cache_file_name
        with cache_file_path.open("w", encoding="utf-8") as f:
            f.write(CachedSchemaRoot(root=cached_schema).model_dump_json(indent=2))
        return cached_schema

    def valid_compatibility_dates(self, session: Client) -> tuple[str, ...]:
        """Return the valid compatibility dates, using the cache if possible."""
        compatibility_dates = self._schema_tool.fetch_compatibility_dates(session)
        return compatibility_dates

    def get_latest_schema(self, session: Client) -> CachedSchema:
        """Get the latest schema, using the cache if possible."""
        compatibility_dates = self._schema_tool.fetch_compatibility_dates(session)
        if not compatibility_dates:
            raise ValueError("No compatibility dates available")
        latest_compatibility_date = max(compatibility_dates)
        cached_schema = self.get_schema(latest_compatibility_date, session)
        if cached_schema is None:
            raise ValueError(
                f"Failed to fetch schema for compatibility date {latest_compatibility_date}"
            )
        return cached_schema

    def get_schema(
        self, compatibility_date: str, session: Client
    ) -> CachedSchema | None:
        """Get a cached schema for the given compatibility date, if it exists and is not expired."""
        # First check that the compatibility date is valid
        compatibility_dates = self._schema_tool.fetch_compatibility_dates(session)
        if compatibility_date not in compatibility_dates:
            raise ValueError(f"Invalid compatibility date: {compatibility_date}")
        # Then check if the schema is in the memory cache and not expired
        cached_schema = self._cached_schemas.get(compatibility_date)
        if cached_schema is not None:
            ttl = self._schema_ttl
            if not cached_schema.is_expired(ttl):
                return cached_schema
            else:
                # Schema is expired, remove it from the cache
                del self._cached_schemas[compatibility_date]
        # If not in cache, check if it exists in the cache directory
        cached_schema_paths = self._cached_schema_paths()
        if compatibility_date in cached_schema_paths:
            cached_schema_path = cached_schema_paths[compatibility_date]
            ttl = self._schema_ttl
            if not cached_schema_path.is_expired(ttl):
                # Load the schema from the file and cache it
                cached_schema = self.get_cached_schema(cached_schema_path)
                if cached_schema is not None:
                    self._cached_schemas[compatibility_date] = cached_schema
                    return cached_schema
        # If not in cache and not in cache directory, fetch it, cache it, and return it
        cached_schema = self._fetch_and_cache_schema(session, compatibility_date)
        return cached_schema

    def list_cached_schemas(self) -> dict[str, CachedSchemaPath]:
        """List the available cached schemas in the cache directory."""
        cached_schema_paths = self._cached_schema_paths()
        return cached_schema_paths

    def get_cached_schema(
        self, cached_schema_path: CachedSchemaPath
    ) -> CachedSchema | None:
        """Get a cached schema from a CachedSchemaPath.

        Does not check if the cached schema is expired.
        """
        with cached_schema_path.file_path.open("r", encoding="utf-8") as f:
            cached_schema = CachedSchemaRoot.model_validate_json(f.read()).root
        return cached_schema

    def clear_cache(self) -> None:
        """Clear the in-memory cache and delete all cached schema files from the cache directory."""
        self._cached_schemas.clear()
        cached_schema_paths = self._cached_schema_paths()
        for cached_schema_path in cached_schema_paths.values():
            try:
                cached_schema_path.file_path.unlink()
            except Exception as e:
                print(
                    f"Error deleting cached schema file {cached_schema_path.file_path}: {e}"
                )
