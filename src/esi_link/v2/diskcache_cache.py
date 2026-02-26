"""A disk-based cache implementation for ESI responses using the diskcache library."""

from pathlib import Path
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from diskcache import Cache  # type: ignore
from whenever import Instant

from esi_link.v2.helpers.stale_cache_check import check_stale
from esi_link.v2.models import (
    CachedResponse,
    CachedResponseStatus,
    CacheManagerProtocol,
    HttpResponse,
)


class DiskCache(CacheManagerProtocol):
    def __init__(self, cache_directory: Path, local_max_age_seconds: int = 3600):
        """A disk-based cache implementation using the diskcache library."""
        self.cache_directory = cache_directory
        self.cache = Cache(cache_directory)
        self.local_max_age_seconds = local_max_age_seconds

    def __enter__(self) -> Self:
        """Enter the runtime context related to this object, which will automatically open the disk cache."""
        self.cache.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the runtime context related to this object, which will automatically close the disk cache."""
        self.cache.__exit__(exc_type, exc_value, traceback)  # type: ignore

    def get(
        self, key: UUID, local_max_age: int | None = None
    ) -> tuple[CachedResponse | None, CachedResponseStatus]:
        """Get a value from the disk cache."""
        if local_max_age is None:
            local_max_age = self.local_max_age_seconds
        response = self.cache.get(str(key))  # type: ignore
        if response is None:
            return None, CachedResponseStatus.MISS
        assert isinstance(response, CachedResponse), (
            "Cached value is not of type CachedResponse"
        )
        if check_stale(response, max_age_seconds=local_max_age):
            return response, CachedResponseStatus.STALE
        return response, CachedResponseStatus.HIT

    def set(self, key: UUID, http_response: HttpResponse) -> None:
        """Set a value in the disk cache."""
        cached_response = CachedResponse(
            cache_key=key,
            cached_on=Instant.now(),
            http_response=http_response,
        )
        self.cache.set(str(key), cached_response)  # type: ignore

    def refresh(self, key: UUID, new_http_response: HttpResponse) -> None:
        """Refresh a value in the disk cache."""
        self.set(key, new_http_response)

    def clear(self) -> int:
        """Clear all cached responses from the cache."""
        return self.cache.clear()

    def cache_info(self) -> dict[str, Any]:
        """Get information about the cache, such as size, number of entries, etc."""
        return {
            "path": self.cache_directory,
            "size": self.cache.volume(),
            "entries": len(self.cache),  # type: ignore
        }
