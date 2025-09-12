"""Cache for Esi get requests."""

import logging
from copy import deepcopy
from uuid import UUID

from whenever import Instant

from esi_link.esi_client.cache_helpers import build_metadata as build_cache_metadata
from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol
from esi_link.helpers import header_funcs as HF

from .link_cache_protocol import CacheStatus, LinkCacheProtocol
from .models import (
    EsiQuery,
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
        self,
        cache_key: UUID,
        cache_metadata: LinkCacheMetadata,
        response: QueryResponse,
    ) -> None:
        """Store a response in the cache with its key."""
        self._cached_responses.data[cache_key] = LinkCachedResponse(
            cache_key=cache_key,
            response=deepcopy(response),
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
            if Instant.parse_rfc2822(metadata.expires) > Instant.now():
                return CacheStatus.HIT
            return CacheStatus.STALE
        return CacheStatus.MISS

    def build_metadata(
        self, query: EsiQuery, response: QueryResponse, schema_api: EsiApiProtocol
    ) -> LinkCacheMetadata:
        return build_cache_metadata(query, response, schema_api)

    def update_304(self, cache_key: UUID, response: QueryResponse) -> None:
        """Update the cache metadata for a 304 response."""

        cached_metadata = self.get_cache_metadata(cache_key)
        if cached_metadata is None:
            raise ValueError(f"Cache key {cache_key} not found in cache.")
        new_metadata = LinkCacheMetadata(
            cache_key=cache_key,
            expires=HF.expires(response.headers),
            etag=HF.etag(response.headers),
            last_modified=HF.last_modified(response.headers),
            last_checked=response.completed_on,
        )
        self._cached_responses.data[cache_key].metadata = new_metadata
