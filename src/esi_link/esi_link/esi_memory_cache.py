"""Cache for Esi get requests."""

import logging
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

from ..helpers.now_utc import now_utc
from .link_cache_protocol import CacheStatus, LinkCacheProtocol
from .models import (
    LinkCache,
    LinkCachedResponse,
    LinkCacheMetadata,
    QueryResponse,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class EsiMemoryCache(LinkCacheProtocol):
    """A simple in-memory cache for ESI responses."""

    def __init__(self) -> None:
        self._cached_responses: LinkCache = LinkCache()

    def get(self, key: UUID) -> LinkCachedResponse | None:
        """Retrieve a cached response by its key."""
        cached_value = self._cached_responses.data.get(key)

        if cached_value:
            logger.info(f"Cache hit for key: {key}")
        else:
            logger.info(f"Cache miss for key: {key}")
        return deepcopy(cached_value)

    def get_response(self, key: UUID) -> QueryResponse | None:
        """Retrieve a cached response by its key."""
        cached_value = self._cached_responses.data.get(key)
        if cached_value is None:
            logger.info(f"Cache miss for key: {key}")
            return None
        return deepcopy(cached_value.response)

    def get_cache_metadata(self, key: UUID) -> LinkCacheMetadata | None:
        """Retrieve cache metadata for a cached response by its key."""
        metadata = self._cached_responses.data.get(key)
        if metadata is None:
            logger.info(f"Cache miss for key: {key}")
            return None
        return deepcopy(metadata.metadata)

    def set(
        self, cache_key: UUID, cache_metadata: LinkCacheMetadata, value: QueryResponse
    ) -> None:
        """Store a response in the cache with its key."""
        self._cached_responses.data[cache_key] = LinkCachedResponse(
            cache_key=cache_key,
            response=deepcopy(value),
            metadata=deepcopy(cache_metadata),
        )

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cached_responses.data.clear()

    def remove(self, key: UUID) -> None:
        """Remove a cached response by its key."""
        self._cached_responses.data.pop(key, None)

    def status(self, cache_key: UUID) -> CacheStatus:
        """Get the cache status of an EsiResponse."""
        if cache_key in self._cached_responses.data:
            metadata = self._cached_responses.data[cache_key].metadata
            if datetime.fromisoformat(metadata.expires).astimezone(UTC) > now_utc():
                return CacheStatus.HIT
            return CacheStatus.STALE
        return CacheStatus.MISS
