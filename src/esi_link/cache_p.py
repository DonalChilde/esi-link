"""Cache implementations for ESI Link."""

import logging
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, Field

from esi_link.models import (
    CachedResponse,
    CacheProtocol,
    EsiLinkError,
    EsiRequest,
    EsiSchema,
    HttpResponse,
)

logger = logging.getLogger(__name__)
ESI_LINK_NAMESPACE = uuid5(NAMESPACE_URL, "esi-link")


class EsiLinkCache(BaseModel):
    """Represents the cache configuration for ESI Link."""

    # Room for expansion in the future
    cache: dict[UUID, CachedResponse] = Field(
        default_factory=dict[UUID, CachedResponse]
    )


###########################################################################
# CacheProtocol Implementations
###########################################################################


class NoOpCache(CacheProtocol):
    """A no-op cache implementation that does not store any responses."""

    def generate_cache_key(
        self, esi_request: EsiRequest, esi_schema: EsiSchema
    ) -> UUID | None:
        """NoOpCache does not generate cache keys."""
        return None

    def is_cached(self, cache_key: UUID) -> bool:
        """NoOpCache never has any cached responses."""
        return False

    def get_cached_response(self, cache_key: UUID) -> CachedResponse | None:
        """NoOpCache never has any cached responses."""
        return None

    def store_http_response(self, cache_key: UUID, http_response: HttpResponse) -> None:
        """NoOpCache does not store any cached responses."""
        pass

    def update_http_response(
        self, cache_key: UUID, http_response: HttpResponse
    ) -> None:
        """NoOpCache does not store any cached responses."""
        pass


class InMemoryCache(CacheProtocol):
    """An in-memory cache implementation for storing ESI responses."""

    # TODO match logging from JsonFileCache

    def __init__(self) -> None:
        """Initialize the in-memory cache."""
        self.esi_link_cache = EsiLinkCache()

    def generate_cache_key(
        self, esi_request: EsiRequest, esi_schema: EsiSchema
    ) -> UUID | None:
        """Generate a cache key for the given ESI request."""
        cache_key = generate_cache_key(esi_request=esi_request, esi_schema=esi_schema)
        return cache_key

    def is_cached(self, cache_key: UUID) -> bool:
        """Check if a response is cached for the given cache key."""
        response = self.esi_link_cache.cache.get(cache_key)
        if response is not None:
            logger.info(f"Cache HIT in InMemoryCache for key {cache_key}")
        else:
            logger.info(f"Cache MISS in InMemoryCache for key {cache_key}")
        return bool(response)

    def get_cached_response(self, cache_key: UUID) -> CachedResponse | None:
        """Retrieve the cached response for the given cache key."""
        response = self.esi_link_cache.cache.get(cache_key)
        if response is not None:
            logger.info(f"Cache HIT in InMemoryCache for key {cache_key}")
        else:
            logger.info(f"Cache MISS in InMemoryCache for key {cache_key}")
        return response

    def store_http_response(self, cache_key: UUID, http_response: HttpResponse) -> None:
        """Store the HTTP response in the cache with the given cache key."""
        cached_response = CachedResponse(
            cache_key=cache_key,
            response=http_response,
        )
        self.esi_link_cache.cache[cached_response.cache_key] = cached_response
        logger.info(f"Stored response in InMemoryCache with key {cache_key}")

    def update_http_response(
        self, cache_key: UUID, http_response: HttpResponse
    ) -> None:
        """Update the HTTP response in the cache with the given cache key."""
        if cache_key in self.esi_link_cache.cache:
            cached_response = self.esi_link_cache.cache[cache_key]
            updated_response = CachedResponse(
                cache_key=cache_key,
                response=http_response,
            )
            updated_response.response.json_data = cached_response.response.json_data
            self.esi_link_cache.cache[cache_key] = updated_response
            logger.info(f"Updated response in InMemoryCache with key {cache_key}")
        else:
            logger.warning(
                f"Attempted to update non-existent cache key {cache_key} in InMemoryCache"
            )


class JsonFileCache(CacheProtocol):
    """A JSON file-based cache implementation for storing ESI responses."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the JSON file cache."""
        self.file_path = file_path
        self.esi_link_cache = None
        self._load_cache()
        if self.esi_link_cache is None:
            raise EsiLinkError("Failed to initialize JsonFileCache.")

    def _load_cache(self) -> None:
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = f.read()
                self.esi_link_cache = EsiLinkCache.model_validate_json(data)
        except FileNotFoundError:
            self.esi_link_cache = EsiLinkCache()
            self._save_cache()
            logger.warning(
                f"Cache file not found. Created new cache at {self.file_path}"
            )
        except Exception as e:
            raise EsiLinkError(f"Failed to load cache from disk: {e}") from e

    def _save_cache(self) -> None:
        if self.file_path.is_dir():
            raise EsiLinkError(f"Cache file path is a directory: {self.file_path}")
        if self.esi_link_cache is None:
            raise EsiLinkError("EsiLinkCache is not initialized.")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            temp_file = self.file_path.with_suffix(".tmp")
            with temp_file.open("w", encoding="utf-8") as f:
                f.write(self.esi_link_cache.model_dump_json(indent=2))
            temp_file.replace(self.file_path)
            temp_file.unlink(missing_ok=True)
        except Exception as e:
            raise EsiLinkError(f"Failed to save cache to disk: {e}") from e

    def generate_cache_key(
        self, esi_request: EsiRequest, esi_schema: EsiSchema
    ) -> UUID | None:
        """Generate a cache key for the given ESI request."""
        cache_key = generate_cache_key(esi_request=esi_request, esi_schema=esi_schema)
        return cache_key

    def is_cached(self, cache_key: UUID) -> bool:
        """Check if a response is cached for the given cache key."""
        if self.esi_link_cache is None:
            raise EsiLinkError("EsiLinkCache is not initialized.")
        response = self.esi_link_cache.cache.get(cache_key)
        if response is not None:
            logger.info(
                f"Cache {cache_key}, {'STALE' if response.is_stale() else 'HIT'} in "
                f"JsonFileCache, expires in {response.response.expires_in():.2f} seconds."
            )
        else:
            logger.info(f"Cache MISS in JsonFileCache for key {cache_key}")
        return bool(response)

    def get_cached_response(self, cache_key: UUID) -> CachedResponse | None:
        """Retrieve the cached response for the given cache key."""
        if self.esi_link_cache is None:
            raise EsiLinkError("EsiLinkCache is not initialized.")
        response = self.esi_link_cache.cache.get(cache_key)
        if response is not None:
            logger.info(
                f"Cache {cache_key}, {'STALE' if response.is_stale() else 'HIT'} in "
                f"JsonFileCache, expires in {response.response.expires_in():.2f} seconds. "
                f"Url: {response.response.url}"
            )
        else:
            logger.info(f"Cache MISS in JsonFileCache for key {cache_key}")
        return response

    def store_http_response(self, cache_key: UUID, http_response: HttpResponse) -> None:
        """Store the HTTP response in the cache with the given cache key."""
        if self.esi_link_cache is None:
            raise EsiLinkError("EsiLinkCache is not initialized.")
        cached_response = CachedResponse(
            cache_key=cache_key,
            response=http_response,
        )
        self.esi_link_cache.cache[cached_response.cache_key] = cached_response
        logger.info(
            f"Stored response in JsonFileCache with key {cache_key} "
            f"expires in {cached_response.response.expires_in():.2f} seconds. "
            f"Url: {http_response.url}"
        )
        self._save_cache()

    def update_http_response(
        self, cache_key: UUID, http_response: HttpResponse
    ) -> None:
        """Update the HTTP response in the cache with the given cache key."""
        if self.esi_link_cache is None:
            raise EsiLinkError("EsiLinkCache is not initialized.")
        if cache_key in self.esi_link_cache.cache:
            cached_response = self.esi_link_cache.cache[cache_key]
            updated_response = CachedResponse(
                cache_key=cache_key,
                response=http_response,
            )
            updated_response.response.json_data = cached_response.response.json_data
            self.esi_link_cache.cache[cache_key] = updated_response
            logger.info(
                f"Updated response in JsonFileCache with key {cache_key}"
                f"expires in {cached_response.response.expires_in():.2f} seconds. "
                f"Url: {http_response.url}"
            )
            self._save_cache()
        else:
            logger.warning(
                f"Attempted to update non-existent cache key {cache_key} in JsonFileCache"
            )


def generate_cache_key(esi_request: EsiRequest, esi_schema: EsiSchema) -> UUID | None:
    """Generate a cache key for the given ESI request.

    Args:
        esi_request: The EsiRequest instance for which to generate the cache key.
        esi_schema: The EsiSchema instance containing the OpenAPI schema.

    Returns:
        A UUID representing the cache key, or None if caching is not applicable.
    """
    key_string = generate_cacheable_string(
        esi_request=esi_request, esi_schema=esi_schema
    )
    if key_string is None:
        return None
    # Generate a UUID based on the key string within the ESI_LINK_NAMESPACE
    cache_key = uuid5(ESI_LINK_NAMESPACE, key_string)
    logger.info(f"Generated cache key {cache_key} for request {key_string}")
    return cache_key


def generate_cacheable_string(
    esi_request: EsiRequest, esi_schema: EsiSchema
) -> str | None:
    """Generate a unique string representation of the ESI request for caching."""
    indexed_operation = esi_schema.operations.get(esi_request.operation_id)
    if not indexed_operation:
        raise EsiLinkError(f"Operation ID not found: {esi_request.operation_id}")
    # Only GET requests are cacheable
    if indexed_operation.method != "GET":
        return None
    # Build a unique string representation of the request
    key_string = f"{indexed_operation.method}:{indexed_operation.operation_id}"
    if esi_request.path_parameters:
        sorted_path_params = sorted(esi_request.path_parameters.items())
        path_params_str = ",".join(f"{k}={v}" for k, v in sorted_path_params)
        key_string += f":{path_params_str}"
    if esi_request.query_parameters:
        sorted_query_params = sorted(esi_request.query_parameters.items())
        query_params_str = ",".join(f"{k}={v}" for k, v in sorted_query_params)
        key_string += f"?{query_params_str}"
    # Generate a UUID based on the key string within the ESI_LINK_NAMESPACE
    logger.info(f"Generated key string for request: {key_string}")
    return key_string


def cache_factory(cache_connection_string: str | None) -> CacheProtocol:
    """Factory function to create a cache instance.

    Returns:
        An instance of CacheProtocol.
    """
    if cache_connection_string is None:
        return NoOpCache()
    cache_specifier, cache_str = cache_connection_string.split(":", 1)

    match cache_specifier:
        case "esi-link-noop":
            logger.info("Using NoOpCache for ESI Link caching.")
            return NoOpCache()
        case "esi-link-memory":
            logger.info("Using InMemoryCache for ESI Link caching.")
            return InMemoryCache()
        case "esi-link-file":
            logger.info(f"Using JsonFileCache for ESI Link caching at {cache_str}")
            return JsonFileCache(file_path=Path(cache_str))
        case _:
            raise EsiLinkError(f"Unknown cache specifier: {cache_specifier}")
    raise EsiLinkError(f"Cache type not implemented: {cache_connection_string}")
