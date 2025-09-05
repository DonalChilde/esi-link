"""Cache for Esi get requests."""

import logging
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Self
from uuid import UUID

from esi_link.esi_client.cache_helpers import build_metadata as build_cache_metadata
from esi_link.esi_client.models import EsiQuery
from esi_link.esi_schema.eve_openapi_protocol import EveOpenApiProtocol
from esi_link.helpers import header_funcs as HF

from ..helpers.now_utc import now_utc
from .link_cache_protocol import CacheStatus, LinkCacheProtocol
from .models import (
    LinkCache,
    LinkCachedResponse,
    LinkCacheMetadata,
    QueryResponse,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class EsiFileCache(LinkCacheProtocol):
    """A simple file-based cache for ESI responses."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._cached_responses: LinkCache | None = None

    def __enter__(self) -> Self:
        """Enter the runtime context and load cache from file."""
        self._cached_responses = self._load_cache()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Exit the runtime context and save the ESI cache to file."""
        self._save_cache()

    def _load_cache(self) -> LinkCache:
        if not self._file_path.is_file():
            logger.info(f"No cache file found at {self._file_path}, starting fresh.")
            return LinkCache(data={})
        result = LinkCache.model_validate_json(self._file_path.read_text())
        return result

    def _save_cache(self) -> None:
        if not self._file_path.parent.exists():
            self._file_path.parent.mkdir(parents=True)
        if self._file_path.is_dir():
            raise ValueError(f"{self._file_path} is a directory, not a file.")
        if self._cached_responses is None:
            raise ValueError("No cache to save.")
        self._file_path.write_text(self._cached_responses.model_dump_json())

    def get(self, key: UUID) -> LinkCachedResponse | None:
        """Retrieve a cached response by its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        cached_value = self._cached_responses.data.get(key)

        if cached_value:
            logger.info(f"Cache hit for key: {key}")
        else:
            logger.info(f"Cache miss for key: {key}")
        return deepcopy(cached_value)

    def get_response(self, key: UUID) -> QueryResponse | None:
        """Retrieve a cached response by its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        cached_value = self._cached_responses.data.get(key)
        if cached_value is None:
            logger.info(f"Cache miss for key: {key}")
            return None
        return deepcopy(cached_value.response)

    def get_cache_metadata(self, key: UUID) -> LinkCacheMetadata | None:
        """Retrieve cache metadata for a cached response by its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        metadata = self._cached_responses.data.get(key)
        if metadata is None:
            logger.info(f"Cache miss for key: {key}")
            return None
        return deepcopy(metadata.metadata)

    def set(
        self, cache_key: UUID, cache_metadata: LinkCacheMetadata, value: QueryResponse
    ) -> None:
        """Store a response in the cache with its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        self._cached_responses.data[cache_key] = LinkCachedResponse(
            cache_key=cache_key,
            response=deepcopy(value),
            metadata=deepcopy(cache_metadata),
        )

    def clear(self) -> None:
        """Clear the entire cache."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        self._cached_responses.data.clear()

    def remove(self, key: UUID) -> None:
        """Remove a cached response by its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        self._cached_responses.data.pop(key, None)

    def status(self, cache_key: UUID) -> CacheStatus:
        """Get the cache status of an EsiResponse."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        if cache_key in self._cached_responses.data:
            metadata = self._cached_responses.data[cache_key].metadata
            if datetime.fromisoformat(metadata.expires).astimezone(UTC) > now_utc():
                return CacheStatus.HIT
            return CacheStatus.STALE
        return CacheStatus.MISS

    def build_metadata(
        self, query: EsiQuery, response: QueryResponse, schema_api: EveOpenApiProtocol
    ) -> LinkCacheMetadata:
        return build_cache_metadata(query, response, schema_api)

    def update_304(self, cache_key: UUID, response: QueryResponse) -> None:
        """Update the cache metadata for a 304 response."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        cached_metadata = self.get_cache_metadata(cache_key)
        if cached_metadata is None:
            raise ValueError(f"Cache key {cache_key} not found in cache.")
        new_metadata = LinkCacheMetadata(
            cache_key=cache_key,
            expires=HF.expires(response.headers),
            etag=HF.etag(response.headers),
            last_modified=HF.last_modified(response.headers),
            last_checked=response.completed_on,
        )
        self._cached_responses.data[cache_key].metadata = new_metadata
