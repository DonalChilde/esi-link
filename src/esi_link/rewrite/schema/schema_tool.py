"""Tools for fetching and processing ESI OpenAPI schemas, including caching compatibility dates and resolving internal references."""

from dataclasses import dataclass
from datetime import date
from typing import Any, TypedDict

from httpx2 import Client
from pydantic import RootModel
from whenever import Instant

from esi_link.rewrite.helpers.eve_dates import latest_schema_date
from esi_link.rewrite.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.rewrite.settings import ESI_SCHEMA_URL

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
        return Instant.now().timestamp() - self.fetch_timestamp > ttl

    def expires_in(self, ttl: int) -> int:
        """Return the number of seconds until the cached compatibility dates expire, or a negative number if they are already expired."""
        return ttl - (Instant.now().timestamp() - self.fetch_timestamp)


class SchemaTool:
    def __init__(
        self,
        compatibility_dates_url: str = COMPATIBILITY_DATES_URL,
        compatibility_date_ttl: int = 3600,
    ):
        """Initialize the SchemaTool."""
        self.compatibility_dates_url = compatibility_dates_url
        self._compatibility_date_ttl = compatibility_date_ttl
        self._cached_compatibility_dates: CachedCompatibilityDates | None = None

    def _is_valid_compatibility_date(self, date_string: str, session: Client) -> bool:
        """Check if a given date string is a valid compatibility date."""
        latest_date = latest_schema_date()
        try:
            date.fromisoformat(date_string)
            if date_string > latest_date:
                return False
            possible_dates = self.fetch_compatibility_dates(session)
            if date_string not in possible_dates["compatibility_dates"]:
                return False
            return True
        except ValueError:
            return False

    def fetch_compatibility_dates(self, session: Client) -> CompatibilityDates:
        """Fetch the compatibility dates from the ESI endpoint."""
        if self._cached_compatibility_dates is not None:
            ttl = self._compatibility_date_ttl
            if not self._cached_compatibility_dates.is_expired(ttl):
                return self._cached_compatibility_dates.compatibility_dates
        response = session.get(self.compatibility_dates_url)
        response.raise_for_status()
        dates = response.json()
        timestamp = Instant.now().timestamp()
        compatibility_dates = CompatibilityDatesRoot.model_validate(dates).root
        self._cached_compatibility_dates = CachedCompatibilityDates(
            compatibility_dates=compatibility_dates, fetch_timestamp=timestamp
        )
        return self._cached_compatibility_dates.compatibility_dates

    def fetch_schema(
        self, session: Client, compatibility_date: str
    ) -> TimestampedSchema:
        """Fetch the ESI OpenAPI schema for a specific compatibility date."""
        if not self._is_valid_compatibility_date(compatibility_date, session):
            raise ValueError(f"Invalid compatibility date: {compatibility_date}")
        url = f"{ESI_SCHEMA_URL}?compatibility_date={compatibility_date}"
        response = session.get(url)
        response.raise_for_status()
        return TimestampedSchema(
            schema=response.json(),
            fetch_timestamp=Instant.now().timestamp(),
        )

    @staticmethod
    def resolve_schema(schema: TimestampedSchema) -> ResolvedTimestampedSchema:
        """Resolve internal references in the ESI OpenAPI schema."""
        resolved_schema = resolve_internal_refs(schema.schema, schema.schema)
        return ResolvedTimestampedSchema(
            schema=resolved_schema,
            fetch_timestamp=schema.fetch_timestamp,
        )
