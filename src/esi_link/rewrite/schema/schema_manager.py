from dataclasses import dataclass
from pathlib import Path
from typing import Self

from pydantic import RootModel
from whenever import Instant

from esi_link.rewrite.schema.models import EsiSchema
from esi_link.rewrite.schema.schema_tool import SchemaTool, TimestampedSchema


@dataclass(slots=True, kw_only=True, frozen=True)
class StoredSchema:
    """Represents a stored ESI schema, including the raw schema and the date it was downloaded."""

    esi_schema: EsiSchema
    download_date: Instant


@dataclass(slots=True, kw_only=True, frozen=True)
class AvailableSchema:
    """Represents an available ESI schema in the SchemaManager.

    Available schemas are returned as a list of AvailableSchema, where each instance contains:
        - compatibility_date (str): The compatibility date of the schema.
        - timestamp (int): The timestamp of the schema download.
        - datetime (str): The download date and time of the schema as an ISO 8601 string.
    """

    compatibility_date: str
    timestamp: int
    datetime: str


StoredSchemaRoot = RootModel[StoredSchema]


# SchemaManager is responsible for managing the ESI schemas, including fetching available schemas,
# downloading schemas, and caching them for future use. It uses the SchemaTool to fetch compatibility
# dates and validate them, and it stores the schemas in a specified directory for later retrieval.
# Only the latest schema for each compatibility date is stored, defined by the download timestamp.
# The schemas are stored in a directory with a defined file naming convention that includes
# the compatibility date and the download timestamp <compatibility_date>_<timestamp>_esi-schema.json.
# On entering context, the manager will scan the schamas directory, and collect the available
# schemas based on the file names, and make them available for retrieval. When a schema
# is requested - by compatibility date and optional at_or_after timestamp, the manager
# will check if it is already cached, and if not, it will download it, store it in the
# directory, and cache it for future use. The manager also provides a method to clear the cache if needed.
class SchemaManager:
    def __init__(self, schemas_directory: Path):
        """Initialize the SchemaManager."""
        self._schemas_directory = schemas_directory
        self._schema_tool = SchemaTool()
        self._available_schemas: list[AvailableSchema] | None = None

    def __enter__(self) -> Self:
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager."""
        self.cached_schemas.clear()
