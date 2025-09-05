"""Eve Argus ESI Cache Protocol."""

from enum import StrEnum
from typing import Protocol
from uuid import UUID

from esi_link.esi_schema.eve_openapi_protocol import EveOpenApiProtocol

from .models import EsiQuery, LinkCachedResponse, LinkCacheMetadata, QueryResponse


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

    def get(self, key: UUID) -> LinkCachedResponse | None:
        """Get an ESI Link cached response from the cache."""
        ...

    def get_response(self, key: UUID) -> QueryResponse | None:
        """Get an ESI query response from the cache by key."""
        ...

    def get_cache_metadata(self, key: UUID) -> LinkCacheMetadata | None:
        """Get the cache metadata for an ESI query response from the cache."""
        ...

    def update_304(self, cache_key: UUID, response: QueryResponse) -> None:
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

    def build_metadata(
        self, query: EsiQuery, response: QueryResponse, schema_api: EveOpenApiProtocol
    ) -> LinkCacheMetadata:
        """Build cache metadata for a QueryResponse."""
        ...
