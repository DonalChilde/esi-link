"""Tools for fetching and processing ESI OpenAPI schemas, including caching compatibility dates and resolving internal references."""

import sqlite3
from dataclasses import dataclass
from typing import TypedDict

from httpx2 import Client
from pydantic import RootModel
from pydantic_core import from_json, to_json
from whenever import Instant

from esi_link.app_data.helpers import transaction
from esi_link.helpers.eve_dates import previous_downtime
from esi_link.settings import COMPATIBILITY_DATES_URL


class CompatibilityDates(TypedDict):
    """Represents the structure of the compatibility dates response from the ESI endpoint."""

    compatibility_dates: list[str]


CompatibilityDatesRoot = RootModel[CompatibilityDates]


@dataclass(slots=True, kw_only=True, frozen=True)
class CachedCompatibilityDates:
    """Represents cached compatibility dates, including the list of dates and the timestamp of when they were fetched."""

    compatibility_dates: CompatibilityDates
    timestamp: int
    """Nanoseconds since the Unix epoch when the compatibility dates were fetched."""

    def is_expired(self, ttl: int) -> bool:
        """Check if the cached compatibility dates have expired based on the provided TTL."""
        return (Instant.now() - self.timestamp_instant).total("seconds") > ttl

    def expires_in(self, ttl: int) -> int:
        """Return the number of seconds until the cached compatibility dates expire, or a negative number if they are already expired."""
        return ttl - int((Instant.now() - self.timestamp_instant).total("seconds"))

    @property
    def timestamp_instant(self) -> Instant:
        """Convert the fetch timestamp to an Instant."""
        return Instant.from_timestamp_nanos(self.timestamp)


class CompatibilityDatesCacheSQLite:
    def __init__(
        self,
        connection: sqlite3.Connection,
        session: Client,
        compatibility_dates_url: str = COMPATIBILITY_DATES_URL,
    ):
        """Initialize the CompatibilityDatesCacheSQLite."""
        self._connection = connection
        self._session = session
        self._compatibility_dates_url = compatibility_dates_url
        self._cached_dates: CachedCompatibilityDates | None = None
        self._init_cached_dates()

    def _init_cached_dates(self) -> None:
        """Initialize the cached compatibility dates from the database, refreshing from the URL if necessary."""
        if self._cached_dates is None:
            cached_dates = self._load_compatibility_dates_from_db()
            if cached_dates is None:
                self._refresh_cached_dates()
        if self._is_cache_expired():
            self._refresh_cached_dates()

    def _refresh_cached_dates(self) -> None:
        """Refresh the cached compatibility dates by fetching from the URL and saving to the database."""
        fetched_dates = self._fetch_compatibility_dates_from_url(session=self._session)
        self._save_compatibility_dates_to_db(fetched_dates)
        self._cached_dates = fetched_dates

    def _load_compatibility_dates_from_db(self) -> CachedCompatibilityDates | None:
        sql = "SELECT timestamped, compatibility_dates_json FROM CompatibilityDatesCache WHERE id = 0"
        with transaction(self._connection) as conn:
            row = conn.execute(sql).fetchone()
            if row is None:
                return None
            timestamped = row["timestamped"]
            compatibility_dates = from_json(row["compatibility_dates_json"])
            return CachedCompatibilityDates(
                compatibility_dates=compatibility_dates, timestamp=timestamped
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
            conn.execute(sql, (cached_dates.timestamp, compatibility_dates_json))

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
            compatibility_dates=compatibility_dates, timestamp=timestamp
        )

    def _is_cache_expired(self) -> bool:
        """Check if the cached compatibility dates have expired based on the previous downtime."""
        if self._cached_dates is None:
            return True
        previous_dt = previous_downtime()
        cached_instant = self._cached_dates.timestamp_instant
        # If the cached compatibility dates were fetched before or at the previous downtime, they are expired.
        return cached_instant <= previous_dt

    @property
    def compatibility_dates(self) -> CachedCompatibilityDates:
        """Get the Esi Schema versioned compatibility dates, either from cache or freshly fetched.

        The cache is updated at most once per downtime, since new compatibility dates
        are only added at downtime.

        These dates represent the available schema versions for the EVE ESI.
        Major changes to the ESI schemas are indicated by new compatibility dates, which are added at downtime.
        Minor changes that do not affect compatibility do not result in new compatibility dates.
        """
        if self._cached_dates is None:
            raise ValueError(
                "Cached compatibility dates should have been initialized by now."
            )
        if self._is_cache_expired():
            self._refresh_cached_dates()
        return self._cached_dates
