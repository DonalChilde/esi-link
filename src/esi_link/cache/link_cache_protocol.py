"""Eve Argus ESI Cache Protocol."""

from enum import StrEnum
from typing import Any, Protocol, Self
from uuid import UUID

from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol

from ..esi_client.models import (
    EsiQuery,
    LinkCachedResponse,
    LinkCacheMetadata,
    QueryResponse,
)


class InvalidCacheRequest(Exception):
    """Raised when an invalid cache request is made."""


class CacheStatus(StrEnum):
    """Represents the cache status of an ESI query."""

    HIT = "hit"
    """A current response is available in the cache."""
    MISS = "miss"
    """The response was not found in cache."""
    STALE = "stale"
    """The cached response is stale and needs to be refreshed."""


class LinkCacheProtocol(Protocol):
    """Protocol for ESI Link cache operations."""

    def __enter__(self) -> Self:
        """Enter the runtime context and load cache from file."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Exit the runtime context and save the ESI cache to file."""
        ...

    def get(self, key: UUID) -> LinkCachedResponse:
        """Get an ESI Link cached response from the cache.

        Args:
            key (UUID): The cache key UUID.

        Returns:
            LinkCachedResponse: The cached response.
        Raises:
            InvalidCacheRequest: If the key is not found in the cache.

        """
        ...

    def get_response(self, key: UUID) -> QueryResponse:
        """Get an ESI query response from the cache by key.

        Args:
            key (UUID): The cache key UUID.
        Returns:
            QueryResponse: The cached response.
        Raises:
            InvalidCacheRequest: If the key is not found in the cache.
        """
        ...

    def get_cache_metadata(self, key: UUID) -> LinkCacheMetadata:
        """Get the cache metadata for an ESI query response from the cache.
        Args:
            key (UUID): The cache key UUID.

        Returns:
            LinkCacheMetadata: The cache metadata.
        Raises:
            InvalidCacheRequest: If the key is not found in the cache.
        """
        ...

    def update_304(self, cache_key: UUID, query: EsiQuery) -> None:
        """Update the cache metadata for a 304 response."""
        ...

    def set(
        self,
        cache_key: UUID,
        cache_metadata: LinkCacheMetadata,
        response: QueryResponse,
    ) -> None:
        """Set a QueryResponse in the cache."""
        ...

    def remove(self, key: UUID) -> None:
        """Remove an ESI query response from the cache."""
        ...

    def clear(self) -> None:
        """Clear the cache."""
        ...

    def status(self, cache_key: UUID) -> CacheStatus:
        """Get the cache status of a query."""
        ...

    def stats(self) -> dict[str, Any]:
        """Get statistics about the cache as a JSON-serializable dict."""
        ...

    def build_metadata(
        self, query: EsiQuery, schema_api: EsiApiProtocol
    ) -> LinkCacheMetadata:
        """Build cache metadata for a QueryResponse."""
        ...
