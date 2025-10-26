import logging
from pathlib import Path
from typing import Optional
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
        return None

    def is_cached(self, cache_key: UUID) -> bool:
        return False

    def get_cached_response(self, cache_key: UUID) -> Optional[CachedResponse]:
        return None

    def store_cached_response(self, cached_response: CachedResponse) -> None:
        pass


class InMemoryCache(CacheProtocol):
    """An in-memory cache implementation for storing ESI responses."""

    def __init__(self) -> None:
        self.esi_link_cache = EsiLinkCache()

    def generate_cache_key(
        self, esi_request: EsiRequest, esi_schema: EsiSchema
    ) -> UUID | None:
        cache_key = generate_cache_key(esi_request=esi_request, esi_schema=esi_schema)
        return cache_key

    def is_cached(self, cache_key: UUID) -> bool:
        return cache_key in self.esi_link_cache.cache

    def get_cached_response(self, cache_key: UUID) -> Optional[CachedResponse]:
        return self.esi_link_cache.cache.get(cache_key)

    def store_http_response(self, cache_key: UUID, http_response: HttpResponse) -> None:
        cached_response = CachedResponse(
            cache_key=cache_key,
            response=http_response,
        )
        self.esi_link_cache.cache[cached_response.cache_key] = cached_response


class JsonFileCache(CacheProtocol):
    """A JSON file-based cache implementation for storing ESI responses."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.esi_link_cache = EsiLinkCache()

    def _load_cache(self) -> None:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = f.read()
                self.esi_link_cache = EsiLinkCache.model_validate_json(data)
        except FileNotFoundError:
            self.esi_link_cache = EsiLinkCache()
            self._save_cache()
        except Exception as e:
            raise EsiLinkError(f"Failed to load cache from disk: {e}") from e

    def _save_cache(self) -> None:
        if self.file_path.is_dir():
            raise EsiLinkError(f"Cache file path is a directory: {self.file_path}")
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
        cache_key = generate_cache_key(esi_request=esi_request, esi_schema=esi_schema)
        return cache_key

    def is_cached(self, cache_key: UUID) -> bool:
        return cache_key in self.esi_link_cache.cache

    def get_cached_response(self, cache_key: UUID) -> Optional[CachedResponse]:
        return self.esi_link_cache.cache.get(cache_key)

    def store_http_response(self, cache_key: UUID, http_response: HttpResponse) -> None:
        cached_response = CachedResponse(
            cache_key=cache_key,
            response=http_response,
        )
        self.esi_link_cache.cache[cached_response.cache_key] = cached_response
        self._save_cache()


def generate_cache_key(esi_request: EsiRequest, esi_schema: EsiSchema) -> UUID | None:
    """Generate a cache key for the given ESI request.

    Args:
        esi_request: The EsiRequest instance for which to generate the cache key.
        esi_schema: The EsiSchema instance containing the OpenAPI schema.
    Returns:
        A UUID representing the cache key, or None if caching is not applicable.
    """
    indexed_operation = esi_schema.operations.get(esi_request.operation_id)
    if not indexed_operation:
        raise EsiLinkError(f"Operation ID not found: {esi_request.operation_id}")
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
    cache_key = uuid5(ESI_LINK_NAMESPACE, key_string)
    return cache_key


def cache_factory(cache_connection_string: str | None) -> CacheProtocol:
    """Factory function to create a cache instance.

    Returns:
        An instance of CacheProtocol.
    """
    if cache_connection_string is None:
        return NoOpCache()
    cache_specifier, cache_str = cache_connection_string.split("://", 1)

    match cache_specifier:
        case "esi-link-noop":
            logger.info("Using NoOpCache for ESI Link caching.")
            return NoOpCache()
        case "esi-link-memory":
            logger.info("Using InMemoryCache for ESI Link caching.")
            return InMemoryCache()
        case "esi-link-json":
            logger.info(f"Using JsonFileCache for ESI Link caching at {cache_str}")
            return JsonFileCache(file_path=Path(cache_str))
        case _:
            raise EsiLinkError(f"Unknown cache specifier: {cache_specifier}")
    raise EsiLinkError(f"Cache type not implemented: {cache_connection_string}")
