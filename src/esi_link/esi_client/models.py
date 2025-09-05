from typing import TypedDict
from uuid import UUID

from pydantic import BaseModel


class EsiQuery(BaseModel):
    query_id: UUID
    operation_id: str
    path_parameters: dict[str, str | int | float] = {}
    query_parameters: dict[str, str | int | float] = {}
    headers: dict[str, str] = {}


class QueryResponse(BaseModel):
    query_id: UUID
    status_code: int
    status_reason: str
    real_url: str
    text: str
    paged_text: list[str] = []
    headers: tuple[tuple[str, str | None], ...] = ()
    completed_on: str


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
    """The last time this ESI route was checked in ISO 8601 format."""


class CacheEntry(BaseModel):
    """Represents a cached entry."""

    metadata: LinkCacheMetadata
    response: str


class LinkCachedResponse(BaseModel):
    """Represents a cached ESI response."""

    cache_key: UUID
    metadata: LinkCacheMetadata
    response: QueryResponse


class LinkCache(BaseModel):
    data: dict[UUID, LinkCachedResponse] = {}
