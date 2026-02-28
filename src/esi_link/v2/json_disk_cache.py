"""A JSON-based disk cache implementation."""

from pathlib import Path
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from whenever import Instant

from esi_link.v2.helpers.stale_cache_check import is_stale
from esi_link.v2.models import (
    CachedResponse,
    CachedResponseStatus,
    CacheManagerProtocol,
    HttpResponse,
)


class JsonDiskCache(CacheManagerProtocol):
    def __init__(self, cache_directory: Path, local_max_age_seconds: int = 3600):
        """A disk-based cache implementation using json files in a single directory.

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
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.local_max_age_seconds = local_max_age_seconds

    def __enter__(self) -> Self:
        """Enter the runtime context related to this object."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the runtime context related to this object."""

    def get(
        self, key: UUID, local_max_age: int | None = None
    ) -> tuple[CachedResponse | None, CachedResponseStatus]:
        """Get a value from the disk cache."""
        if local_max_age is None:
            local_max_age = self.local_max_age_seconds
        response_path = self.cache_directory.joinpath(f"{key}.json")
        if not response_path.exists():
            return None, CachedResponseStatus.MISS
        response = CachedResponse.model_validate_json(response_path.read_text())
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
        response_path = self.cache_directory.joinpath(f"{key}.json")
        response_path.write_text(cached_response.model_dump_json())
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
        count = 0
        for file in self.cache_directory.glob("*.json"):
            if only_stale:
                response = CachedResponse.model_validate_json(file.read_text())
                if not is_stale(
                    response, local_max_age_seconds=self.local_max_age_seconds
                ):
                    continue
            file.unlink()
            count += 1
        return count

    def cache_info(self) -> dict[str, Any]:
        """Get information about the cache, such as size, number of entries, etc."""
        directory_size = sum(
            file.stat().st_size for file in self.cache_directory.glob("*.json")
        )
        return {
            "path": self.cache_directory,
            "size": directory_size,
            "entries": len(list(self.cache_directory.glob("*.json"))),
        }
