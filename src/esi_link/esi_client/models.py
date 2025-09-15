from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ResponseSource(StrEnum):
    """Indicates the source of a response."""

    CACHE = "cache"
    """The response was served from cache."""
    LIVE = "live"
    """The response was served from the live ESI API."""
    LIVE_304 = "live_304"
    """The response was served from the live ESI API with a 304 Not Modified status."""
    NOT_SET = "not_set"
    """The response source is not set."""


class QueryResponse(BaseModel):
    """Represents a raw response from an ESI query."""

    status_code: int
    status_reason: str
    real_url: str
    text: str
    paged_text: list[str] = []
    headers: tuple[tuple[str, str | None], ...] = ()
    completed_on: str
    source: ResponseSource = ResponseSource.NOT_SET


class QueryResponseResult(BaseModel):
    """Represents a parsed JSON response from an ESI query."""

    status_code: int
    status_reason: str
    real_url: str
    data: Any
    """The query response data parsed as JSON."""
    headers: tuple[tuple[str, str | None], ...] = ()
    completed_on: str
    source: ResponseSource = ResponseSource.NOT_SET


class EsiQuery(BaseModel):
    """Represents an ESI query. If the response is not None, the query has been made."""

    query_id: UUID
    operation_id: str
    path_parameters: dict[str, str | int | float] = {}
    query_parameters: dict[str, str | int | float] = {}
    request_body: dict[str, str | int | float] = {}  # TODO this might need new types.
    headers: dict[str, str] = {}
    response: QueryResponse | None = None


class EsiQueryResult(BaseModel):
    """Represents the result of an ESI query."""

    query_id: UUID
    operation_id: str
    path_parameters: dict[str, str | int | float] = {}
    query_parameters: dict[str, str | int | float] = {}
    request_body: dict[str, str | int | float] = {}  # TODO this might need new types.
    headers: dict[str, str] = {}
    response: QueryResponseResult


class LinkCacheMetadata(BaseModel):
    """Represents a cache metadata for ESI GET requests/responses."""

    cache_key: UUID
    """The cache key UUID, built from the get request url."""
    url: str
    """The full URL for the GET request."""
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
