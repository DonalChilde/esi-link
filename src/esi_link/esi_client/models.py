from typing import Any
from uuid import UUID

from pydantic import BaseModel


class QueryResponse(BaseModel):
    """Represents a raw response from an ESI query."""

    status_code: int
    status_reason: str
    real_url: str
    text: str
    paged_text: list[str] = []
    headers: tuple[tuple[str, str | None], ...] = ()
    completed_on: str


class QueryResponseJson(BaseModel):
    """Represents a parsed JSON response from an ESI query."""

    status_code: int
    status_reason: str
    real_url: str
    data: Any
    """The query response data parsed as JSON."""
    headers: tuple[tuple[str, str | None], ...] = ()
    completed_on: str


class EsiQuery(BaseModel):
    """Represents an ESI query. If the response is not None, the query has been made."""

    query_id: UUID
    operation_id: str
    path_parameters: dict[str, str | int | float] = {}
    query_parameters: dict[str, str | int | float] = {}
    request_body: dict[str, str | int | float] = {}  # TODO this might need new types.
    headers: dict[str, str] = {}
    response: QueryResponse | QueryResponseJson | None = None


class LinkCacheMetadata(BaseModel):
    """Represents a cache metadata for ESI GET requests/responses."""

    cache_key: UUID
    """The cache key UUID, built from the get request url."""
    expires: str
    """The expiration time for the cache key."""
    etag: str
    """The ETag for the cached response."""
    last_modified: str
    """The last modified time for the cached response."""
    last_checked: str
    """The last time this ESI route was checked in rfc 2822 format."""


# class CacheEntry(BaseModel):
#     """Represents a cached entry."""

#     metadata: LinkCacheMetadata
#     response: str


class LinkCachedResponse(BaseModel):
    """Represents a cached ESI response."""

    cache_key: UUID
    metadata: LinkCacheMetadata
    response: QueryResponse


class LinkCache(BaseModel):
    data: dict[UUID, LinkCachedResponse] = {}
