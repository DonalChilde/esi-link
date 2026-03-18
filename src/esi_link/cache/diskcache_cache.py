"""A disk-based cache implementation for ESI responses using the diskcache library."""

from pathlib import Path
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from diskcache import Cache  # type: ignore
from whenever import Instant

from esi_link.cache.stale_cache_check import is_stale
from esi_link.models_and_protocols import (
    CachedResponse,
    CachedResponseStatus,
    CacheManagerProtocol,
    HttpResponse,
)


class DiskCache(CacheManagerProtocol):
    def __init__(self, cache_directory: Path, local_max_age_seconds: int = 3600):
        """A disk-based cache implementation using the diskcache library.

        Local expiration checks can be performed using the local_max_age_seconds parameter,
        which determines how long a cached response is considered fresh before it is
        treated as stale. This allows for more aggressive cache invalidation based on
        local rules, in addition to the standard HTTP caching headers.

        Args:
            cache_directory: The directory where cached responses will be stored.
            local_max_age_seconds: The maximum age in seconds for a cached response to
                be considered fresh. This is used for local expiration checks before considering the response stale based on its expires_at value.
        """
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
        if is_stale(response, local_max_age_seconds=local_max_age):
            return response, CachedResponseStatus.STALE
        return response, CachedResponseStatus.HIT

    def set(self, key: UUID, http_response: HttpResponse) -> CachedResponse:
        """Set a value in the disk cache."""
        cached_response = CachedResponse(
            cache_key=key,
            cached_at=Instant.now(),
            http_response=http_response,
            expires_at=http_response.expires_at,
        )
        self.cache.set(str(key), cached_response)  # type: ignore
        return cached_response

    def refresh(self, key: UUID, new_http_response: HttpResponse) -> CachedResponse:
        """Refresh a value in the disk cache."""
        cached_response, _ = self.get(key)
        if cached_response is None:
            raise KeyError(f"No cached response found for key {key} to refresh.")
        data = cached_response.http_response.body_text
        updated_http_response = HttpResponse(
            status_code=new_http_response.status_code,
            url=new_http_response.url,
            headers=new_http_response.headers,
            body_text=data,
            received_at=new_http_response.received_at,
        )
        return self.set(key, updated_http_response)

    def clear(self, only_stale: bool = False) -> int:
        """Clear all cached responses from the cache."""
        if only_stale:
            keys_to_delete: list[str] = [
                key
                for key, response in self.cache.items()  # type: ignore
                if is_stale(response, local_max_age_seconds=self.local_max_age_seconds)  # type: ignore
            ]
            for key in keys_to_delete:
                self.cache.delete(key)  # type: ignore
            return len(keys_to_delete)
        return self.cache.clear()

    def cache_info(self) -> dict[str, Any]:
        """Get information about the cache, such as size, number of entries, etc."""
        return {
            "path": self.cache_directory,
            "size": self.cache.volume(),
            "entries": len(self.cache),  # type: ignore
        }
