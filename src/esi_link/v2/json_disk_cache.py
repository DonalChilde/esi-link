"""A JSON-based disk cache implementation."""

from pathlib import Path
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from whenever import Instant

from esi_link.v2.helpers.stale_cache_check import check_stale
from esi_link.v2.models import (
    CachedResponse,
    CachedResponseStatus,
    CacheManagerProtocol,
    HttpResponse,
)


class JsonDiskCache(CacheManagerProtocol):
    def __init__(self, cache_directory: Path, local_max_age_seconds: int = 3600):
        """A disk-based cache implementation using json files."""
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
        response_path = self.cache_directory.joinpath(f"{key}.json")
        response_path.write_text(cached_response.model_dump_json())

    def refresh(self, key: UUID, new_http_response: HttpResponse) -> None:
        """Refresh a value in the disk cache."""
        self.set(key, new_http_response)

    def clear(self) -> int:
        """Clear all cached responses from the cache."""
        count = 0
        for file in self.cache_directory.glob("*.json"):
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
