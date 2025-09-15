"""Cache for Esi get requests."""

import logging
from copy import deepcopy
from typing import Any, Self
from uuid import UUID

from whenever import Instant

from esi_link.esi_client.cache_helpers import build_metadata as build_cache_metadata
from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol
from esi_link.helpers import header_funcs as HF

from .link_cache_protocol import CacheStatus, InvalidCacheRequest, LinkCacheProtocol
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

    def __enter__(self) -> Self:
        """Enter the runtime context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Exit the runtime context."""
        pass

    def get(self, key: UUID) -> LinkCachedResponse:
        """Retrieve a cached response by its key."""
        cached_value = self._cached_responses.data.get(key)
        if cached_value is None:
            logger.warning(f"Cache miss for key: {key}, check cache status first.")
            raise InvalidCacheRequest(f"Cache key {key} not found in cache.")
        return deepcopy(cached_value)

    def get_response(self, key: UUID) -> QueryResponse:
        """Retrieve a cached response by its key."""
        cached_value = self._cached_responses.data.get(key)
        if cached_value is None:
            logger.warning(f"Cache miss for key: {key}, check cache status first.")
            raise InvalidCacheRequest(f"Cache key {key} not found in cache.")
        return deepcopy(cached_value.response)

    def get_cache_metadata(self, key: UUID) -> LinkCacheMetadata:
        """Retrieve cache metadata for a cached response by its key."""
        metadata = self._cached_responses.data.get(key)
        if metadata is None:
            logger.warning(f"Cache miss for key: {key}, check cache status first.")
            raise InvalidCacheRequest(f"Cache key {key} not found in cache.")
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

    def stats(self) -> dict[str, Any]:
        """Get statistics about the cache as a JSON-serializable dict."""
        total_entries = len(self._cached_responses.data)
        total_entries = len(self._cached_responses.data)
        loaded_size_bytes = "NA"
        return {
            "total_entries": total_entries,
            "loaded_size_bytes": loaded_size_bytes,
            "load_time_seconds": "NA",
        }

    def build_metadata(
        self, query: EsiQuery, schema_api: EsiApiProtocol
    ) -> LinkCacheMetadata:
        return build_cache_metadata(query, schema_api)

    def update_304(self, cache_key: UUID, query: EsiQuery) -> None:
        """Update the cache metadata for a 304 response."""
        try:
            # Raise an error if there is no existing cache entry.
            _ = self.get_cache_metadata(cache_key)
        except InvalidCacheRequest as e:
            logger.error(
                f"Cannot 304 update metadata, no cache entry for cache key: {cache_key}"
            )
            raise e from e
        if query.response is None:
            raise ValueError("Response data is None, cannot update metadata.")
        new_metadata = LinkCacheMetadata(
            cache_key=cache_key,
            url=query.response.real_url,
            expires=HF.expires(query.response.headers),
            etag=HF.etag(query.response.headers),
            last_modified=HF.last_modified(query.response.headers),
            last_checked=query.response.completed_on,
        )
        self._cached_responses.data[cache_key].metadata = new_metadata
        cached_response = self._cached_responses.data[cache_key].response
        query_response = deepcopy(query.response)
        # Preserve any paged text already in the cache.
        query_response.text = cached_response.text
        query_response.paged_text = cached_response.paged_text
        # cache the new response with old text data.
        self._cached_responses.data[cache_key].response = query_response
