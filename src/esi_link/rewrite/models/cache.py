from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from whenever import Instant

from esi_link.rewrite.models.http_response import HttpResponse


@dataclass(slots=True, kw_only=True, frozen=True)
class CachedResponse:
    """Represents a cached response for a Request."""

    cache_key: UUID
    cached_at: Instant = field(default_factory=Instant.now)
    """The instant when the response was cached."""
    http_response: HttpResponse
    expires_at: Instant | None = None
    """The instant when the cached response expires and should be considered stale."""

    @property
    def is_expired(self) -> bool:
        """Determine if the cached response is expired based on the current time and the expires_at instant."""
        if self.expires_at is None:
            return False
        return Instant.now() >= self.expires_at

    @property
    def cache_age(self) -> float:
        """Calculate the age of the cached response in seconds."""
        return (Instant.now() - self.cached_at).total("seconds")


class CachedResponseStatus(StrEnum):
    HIT = "HIT"
    MISS = "MISS"
    STALE = "STALE"


class CacheAction(StrEnum):
    ADDED_TO_CACHE = "ADDED_TO_CACHE"
    CACHED_RESPONSE_USED = "CACHED_RESPONSE_USED"
    CACHE_304_REFRESH = "CACHE_304_REFRESH"
