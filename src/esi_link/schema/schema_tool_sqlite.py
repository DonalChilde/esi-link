"""Tools for fetching and processing ESI OpenAPI schemas, including caching compatibility dates and resolving internal references."""

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any, TypedDict

from httpx2 import Client
from pydantic import RootModel
from pydantic_core import from_json, to_json
from whenever import Instant

from esi_link.app_data.helpers import transaction
from esi_link.helpers.eve_dates import latest_schema_date
from esi_link.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.settings import ESI_SCHEMA_URL

COMPATIBILITY_DATES_URL = "https://esi.evetech.net/meta/compatibility-dates"


class CompatibilityDates(TypedDict):
    """Represents the structure of the compatibility dates response from the ESI endpoint."""

    compatibility_dates: list[str]


CompatibilityDatesRoot = RootModel[CompatibilityDates]


@dataclass(slots=True, kw_only=True, frozen=True)
class TimestampedSchema:
    """The ESI schema along with the timestamp of when it was fetched."""

    schema: dict[str, Any]
    fetch_timestamp: int
    """Seconds since the Unix epoch when the schema was fetched."""


@dataclass(slots=True, kw_only=True, frozen=True)
class ResolvedTimestampedSchema:
    """The ESI schema along with the timestamp of when it was fetched."""

    schema: dict[str, Any]
    fetch_timestamp: int
    """Seconds since the Unix epoch when the schema was fetched."""


@dataclass(slots=True, kw_only=True, frozen=True)
class CachedCompatibilityDates:
    """Represents cached compatibility dates, including the list of dates and the timestamp of when they were fetched."""

    compatibility_dates: CompatibilityDates
    fetch_timestamp: int
    """Seconds since the Unix epoch when the compatibility dates were fetched."""

    def is_expired(self, ttl: int) -> bool:
        """Check if the cached compatibility dates have expired based on the provided TTL."""
        return (Instant.now() - self.timestamp_instant).total("seconds") > ttl

    def expires_in(self, ttl: int) -> int:
        """Return the number of seconds until the cached compatibility dates expire, or a negative number if they are already expired."""
        return ttl - int((Instant.now() - self.timestamp_instant).total("seconds"))

    @property
    def timestamp_instant(self) -> Instant:
        """Convert the fetch timestamp to an Instant."""
        return Instant.from_timestamp_nanos(self.fetch_timestamp)


class SchemaToolSqlite:
    def __init__(
        self,
        connection: sqlite3.Connection,
        compatibility_dates_url: str = COMPATIBILITY_DATES_URL,
        compatibility_date_ttl: int = 86400,
    ):
        """Initialize the SchemaTool."""
        self._connection = connection
        self._compatibility_dates_url = compatibility_dates_url
        self._compatibility_date_ttl = compatibility_date_ttl
        # self._cached_compatibility_dates: CachedCompatibilityDates | None = None

    def _load_compatibility_dates_from_db(self) -> CachedCompatibilityDates | None:
        sql = "SELECT timestamped, compatibility_dates_json FROM CompatibilityDatesCache WHERE id = 0"
        with transaction(self._connection) as conn:
            row = conn.execute(sql).fetchone()
            if row is None:
                return None
            timestamped = row["timestamped"]
            compatibility_dates = from_json(row["compatibility_dates_json"])
            return CachedCompatibilityDates(
                compatibility_dates=compatibility_dates, fetch_timestamp=timestamped
            )

    def _save_compatibility_dates_to_db(
        self, cached_dates: CachedCompatibilityDates
    ) -> None:
        compatibility_dates_json = to_json(cached_dates.compatibility_dates)
        sql = """
        REPLACE INTO CompatibilityDatesCache (id, timestamped, compatibility_dates_json)
        VALUES (0, ?, ?)
        """
        with transaction(self._connection) as conn:
            conn.execute(sql, (cached_dates.fetch_timestamp, compatibility_dates_json))

    def _is_valid_compatibility_date(
        self, date_string: str, *, session: Client
    ) -> bool:
        """Check if a given date string is a valid compatibility date."""
        latest_date = latest_schema_date()
        try:
            date.fromisoformat(date_string)
            if date_string > latest_date:
                return False
            possible_dates = self.compatibility_dates(session=session)
            if date_string not in possible_dates.compatibility_dates:
                return False
            return True
        except ValueError:
            return False

    def _fetch_compatibility_dates_from_url(
        self, *, session: Client
    ) -> CachedCompatibilityDates:
        """Fetch the compatibility dates from the URL."""
        response = session.get(self._compatibility_dates_url)
        response.raise_for_status()
        dates = response.json()
        # Sort the dates in ascending order, so order is guaranteed.
        dates["compatibility_dates"].sort()
        timestamp = Instant.now().timestamp_nanos()
        compatibility_dates = CompatibilityDatesRoot.model_validate(dates).root
        return CachedCompatibilityDates(
            compatibility_dates=compatibility_dates, fetch_timestamp=timestamp
        )

    def compatibility_dates(self, session: Client) -> CachedCompatibilityDates:
        """Get the compatibility dates, either from cache or freshly fetched."""
        cached_dates = self._load_compatibility_dates_from_db()
        if cached_dates is not None and not cached_dates.is_expired(
            self._compatibility_date_ttl
        ):
            return cached_dates
        fetched_dates = self._fetch_compatibility_dates_from_url(session=session)
        self._save_compatibility_dates_to_db(fetched_dates)
        return fetched_dates

    def fetch_schema(
        self, compatibility_date: str, *, session: Client
    ) -> TimestampedSchema:
        """Fetch the ESI OpenAPI schema for a specific compatibility date."""
        if not self._is_valid_compatibility_date(compatibility_date, session=session):
            raise ValueError(f"Invalid compatibility date: {compatibility_date}")
        timestamped_schema = self._fetch_schema_for_date(
            compatibility_date=compatibility_date, session=session
        )
        return timestamped_schema

    @staticmethod
    def _fetch_schema_for_date(
        compatibility_date: str, *, session: Client
    ) -> TimestampedSchema:
        """Fetch the ESI OpenAPI schema for a specific compatibility date. This is a helper method for fetch_latest_schema."""
        url = f"{ESI_SCHEMA_URL}?compatibility_date={compatibility_date}"
        response = session.get(url)
        response.raise_for_status()
        return TimestampedSchema(
            schema=response.json(),
            fetch_timestamp=Instant.now().timestamp(),
        )

    @classmethod
    def fetch_latest_schema(cls, *, session: Client) -> TimestampedSchema:
        """Fetch the ESI OpenAPI schema for the latest compatibility date."""
        latest_date = latest_schema_date()
        timestamped_schema = cls._fetch_schema_for_date(
            compatibility_date=latest_date, session=session
        )
        return timestamped_schema

    @staticmethod
    def resolve_schema(schema: TimestampedSchema) -> ResolvedTimestampedSchema:
        """Resolve internal references in the ESI OpenAPI schema."""
        resolved_schema = resolve_internal_refs(schema.schema, schema.schema)
        return ResolvedTimestampedSchema(
            schema=resolved_schema,
            fetch_timestamp=schema.fetch_timestamp,
        )
