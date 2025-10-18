from typing import Optional
from uuid import NAMESPACE_URL, UUID, uuid5

from whenever import Instant

from esi_link.models import (
    CachedResponse,
    CacheProtocol,
    EsiLinkError,
    EsiRequest,
    EsiSchema,
    HttpResponse,
)

ESI_LINK_NAMESPACE = uuid5(NAMESPACE_URL, "esi-link")
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

    def update_cached_response(
        self, cache_key: UUID, http_response: HttpResponse
    ) -> None:
        pass


class InMemoryCache(CacheProtocol):
    """An in-memory cache implementation for storing ESI responses."""

    def __init__(self) -> None:
        self.cache: dict[UUID, CachedResponse] = {}

    def generate_cache_key(
        self, esi_request: EsiRequest, esi_schema: EsiSchema
    ) -> UUID | None:
        cache_key = generate_cache_key(esi_request=esi_request, esi_schema=esi_schema)
        return cache_key

    def is_cached(self, cache_key: UUID) -> bool:
        return cache_key in self.cache

    def get_cached_response(self, cache_key: UUID) -> Optional[CachedResponse]:
        return self.cache.get(cache_key)

    def store_cached_response(self, cached_response: CachedResponse) -> None:
        self.cache[cached_response.cache_key] = cached_response

    def update_cached_response(
        self, cache_key: UUID, http_response: HttpResponse
    ) -> None:
        if cache_key in self.cache:
            cached_response = self.cache[cache_key]
            cached_response.response = http_response
            cached_response.cached_on = Instant.now()
            self.cache[cache_key] = cached_response


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
