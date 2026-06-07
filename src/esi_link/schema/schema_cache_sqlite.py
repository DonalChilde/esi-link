import sqlite3
from dataclasses import dataclass

from pydantic import RootModel
from pydantic_core import from_json, to_json
from whenever import Instant

from esi_link.app_data.helpers import transaction
from esi_link.schema.models import EsiSchema
from esi_link.schema.schema_tool_sqlite import SchemaToolSqlite


@dataclass(slots=True, kw_only=True, frozen=True)
class CachedSchema:
    """Represents a cached ESI schema, including the raw schema and the date it was downloaded."""

    esi_schema: EsiSchema
    timestamp: int
    """Nanoseconds since the Unix epoch when the schema was fetched."""

    def is_expired(self, ttl: int) -> bool:
        """Check if the cached schema has expired based on the provided TTL."""
        return (Instant.now() - self.timestamp_instant).total("seconds") > ttl

    def expires_in(self, ttl: int) -> int:
        """Return the number of seconds until the cached schema expires, or a negative number if it is already expired."""
        return ttl - int((Instant.now() - self.timestamp_instant).total("seconds"))

    @property
    def timestamp_instant(self) -> Instant:
        """Return the timestamp of when the schema was fetched as an Instant."""
        return Instant.from_timestamp_nanos(self.timestamp)

    def to_string(self, indent: int) -> str:
        """Return a string representation of the cached schema with the specified indentation."""
        root_model = CachedSchemaRoot(self)
        json_str = root_model.model_dump_json(indent=indent)
        return json_str

    @classmethod
    def from_string(cls, json_str: str) -> CachedSchema:
        """Parse the cached schema from a JSON string."""
        value = CachedSchemaRoot.model_validate_json(json_str).root
        return value


CachedSchemaRoot = RootModel[CachedSchema]


class SchemaCacheSqlite:
    def __init__(self, connection: sqlite3.Connection):
        """A simple schema cache that stores ESI schema data in a SQLite database."""
        self._connection = connection
        self._schema_tool = SchemaToolSqlite(connection)
