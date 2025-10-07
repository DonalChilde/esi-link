"""Cache for Esi get requests."""

import logging
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from typing import Any, Self
from uuid import UUID

from whenever import Instant

from esi_link.cache.cache_helpers import build_metadata as build_cache_metadata
from esi_link.esi_client.models import EsiQuery
from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol
from esi_link.helpers import header_funcs as HF
from esi_link.helpers.human_readable_file_size import file_size
from esi_link.helpers.validate_file_out import validate_file_out

from ..esi_client.models import (
    LinkCache,
    LinkCachedResponse,
    LinkCacheMetadata,
    QueryResponse,
)
from .link_cache_protocol import CacheStatus, InvalidCacheRequest, LinkCacheProtocol

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class EsiFileCache(LinkCacheProtocol):
    """A simple file-based cache for ESI responses."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._cached_responses: LinkCache | None = None
        self._load_time: float = 0.0
        if not self._file_path.is_file():
            validate_file_out(self._file_path)
            self._cached_responses = LinkCache(data={})
            self._save_cache()
            logger.info(f"Created new cache file at {self._file_path}")

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
        self._cached_responses = None

    def _load_cache(self) -> LinkCache:
        start = perf_counter()
        if not self._file_path.is_file():
            logger.info(f"No cache file found at {self._file_path}, starting fresh.")
            return LinkCache(data={})
        result = LinkCache.model_validate_json(self._file_path.read_text())
        end = perf_counter()
        self._load_time = end - start
        logger.info(
            f"Cache loaded from {self._file_path} in {self._load_time:.2f} seconds, {len(result.data)} entries, {self._file_path.stat().st_size:,} bytes."
        )
        return result

    def _save_cache(self) -> None:
        start = perf_counter()
        if not self._file_path.parent.exists():
            self._file_path.parent.mkdir(parents=True)
        if self._file_path.is_dir():
            raise ValueError(f"{self._file_path} is a directory, not a file.")
        if self._cached_responses is None:
            raise ValueError("No cache to save.")
        self._file_path.write_text(self._cached_responses.model_dump_json())
        logger.info(
            f"Cache saved to {self._file_path} in {perf_counter() - start:.2f} seconds, {len(self._cached_responses.data)} entries, {self._file_path.stat().st_size:,} bytes."
        )

    def get(self, key: UUID) -> LinkCachedResponse:
        """Retrieve a cached response by its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        cached_value = self._cached_responses.data.get(key)
        if cached_value is None:
            logger.warning(f"Cache miss for key: {key}, check cache status first.")
            raise InvalidCacheRequest(f"Cache key {key} not found in cache.")
        return deepcopy(cached_value)

    def get_response(self, key: UUID) -> QueryResponse:
        """Retrieve a cached response by its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        cached_value = self._cached_responses.data.get(key)
        if cached_value is None:
            logger.warning(f"Cache miss for key: {key}, check cache status first.")
            raise InvalidCacheRequest(f"Cache key {key} not found in cache.")
        return deepcopy(cached_value.response)

    def get_cache_metadata(self, key: UUID) -> LinkCacheMetadata:
        """Retrieve cache metadata for a cached response by its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        metadata = self._cached_responses.data.get(key)
        if metadata is None:
            logger.warning(f"Cache miss for key: {key}, check cache status first.")
            raise InvalidCacheRequest(f"Cache key {key} not found in cache.")
        return deepcopy(metadata.metadata)

    def set(
        self,
        cache_key: UUID,
        cache_metadata: LinkCacheMetadata,
        response: QueryResponse,
    ) -> None:
        """Store a response in the cache with its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        self._cached_responses.data[cache_key] = LinkCachedResponse(
            cache_key=cache_key,
            response=deepcopy(response),
            metadata=deepcopy(cache_metadata),
        )
        til_expiration = Instant.parse_rfc2822(cache_metadata.expires) - Instant.now()
        logger.info(
            f"Cache set for key: {cache_key}, url: {cache_metadata.url}, expires at {cache_metadata.expires} in {til_expiration.in_seconds():.2f} seconds."
        )

    def clear(self) -> None:
        """Clear the entire cache."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        self._cached_responses.data.clear()
        logger.info("Cache cleared.")

    def remove(self, key: UUID) -> None:
        """Remove a cached response by its key."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        self._cached_responses.data.pop(key, None)
        logger.info(f"Cache removed for key: {key}")

    def status(self, cache_key: UUID) -> CacheStatus:
        """Get the cache status of an EsiResponse."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        if cache_key in self._cached_responses.data:
            metadata = self._cached_responses.data[cache_key].metadata
            til_expiration = Instant.parse_rfc2822(metadata.expires) - Instant.now()
            if til_expiration.in_seconds() > 0:
                logger.info(
                    f"Cache hit for key: {cache_key}, url: {metadata.url}, expires at {metadata.expires} in {til_expiration.in_seconds():.2f} seconds."
                )
                return CacheStatus.HIT
            logger.info(
                f"Cache stale for key: {cache_key}, url: {metadata.url}, expired at {metadata.expires}, {til_expiration.in_seconds() * -1:.2f} seconds ago"
            )
            return CacheStatus.STALE
        logger.info(f"Cache miss for key: {cache_key}")
        return CacheStatus.MISS

    def stats(self) -> dict[str, Any]:
        """Get statistics about the cache as a JSON-serializable dict."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        total_entries = len(self._cached_responses.data)
        loaded_size_bytes = file_size(self._file_path)
        return {
            "total_entries": total_entries,
            "loaded_size_bytes": loaded_size_bytes,
            "load_time_seconds": f"{self._load_time:.6f}",
        }

    def build_metadata(
        self, query: EsiQuery, schema_api: EsiApiProtocol
    ) -> LinkCacheMetadata:
        return build_cache_metadata(query, schema_api)

    def update_304(self, cache_key: UUID, query: EsiQuery) -> None:
        """Update the cache metadata for a 304 response."""
        if self._cached_responses is None:
            raise ValueError("No cache loaded.")
        try:
            # Raise an error if there is no existing cache entry.
            _ = self.get_cache_metadata(cache_key)
        except InvalidCacheRequest as e:
            logger.error(
                f"Cannot 304 update metadata, no cache entry for cache key: {cache_key}"
            )
            raise e from e
        if query.response is None:
            raise ValueError("Response data is None, cannot update metadata.")
        new_metadata = LinkCacheMetadata(
            cache_key=cache_key,
            url=query.response.real_url,
            expires=HF.expires(query.response.headers),
            etag=HF.etag(query.response.headers),
            last_modified=HF.last_modified(query.response.headers),
            last_checked=query.response.completed_on,
        )
        self._cached_responses.data[cache_key].metadata = new_metadata
        cached_response = self._cached_responses.data[cache_key].response
        query_response = deepcopy(query.response)
        # Preserve any paged text already in the cache.
        query_response.text = cached_response.text
        query_response.paged_text = cached_response.paged_text
        # cache the new response with old text data.
        self._cached_responses.data[cache_key].response = query_response
        til_expiration = Instant.parse_rfc2822(new_metadata.expires) - Instant.now()
        logger.info(
            f"Cache metadata updated for key: {cache_key}, url: {new_metadata.url}, expires at {new_metadata.expires} in {til_expiration.in_seconds():.2f} seconds."
        )
