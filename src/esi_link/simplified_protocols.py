from types import TracebackType
from typing import Any, Self
from uuid import UUID

from whenever import Instant

from esi_link.simplified_models import (
    AvailableSchema,
    CachedResponse,
    EsiSchema,
    HttpResponse,
    StoredSchema,
)


# TODO match this with current implementation
class SchemaManagerProtocol:
    """Protocol for managing ESI schemas, including storing, retrieving, and adding schemas to the schema store.

    While the Esi schema is versioned by its compatibility date, minor changes do not
    trigger an update of the compatibility date. This means that multiple versions of
    the schema can exist for the same compatibility date.

    To avoid ambiguity when multiple versions of the schema exist for the same compatibility date,
    schemas in the store are indexed by both their compatibility date and their download
    timestamp, to allow for retrieval of specific versions of the schema.
    """

    def get_schema(
        self,
        compatibility_date: str | None,
        at_or_after: int | None,
        exact: bool = False,
    ) -> StoredSchema:
        """Get a schema from the store by compatibility date and timestamp.

        This method retrieves a schema from the store based on the provided compatibility date and timestamp criteria. If multiple schemas match the criteria, the most recent one (based on download timestamp) will be returned.

        Args:
            compatibility_date (str | None): The compatibility date of the schema to retrieve. If None, the latest schema across all compatibility dates will be returned.
            at_or_after (int | None): The timestamp of the schema to retrieve, or None to get the latest schema for the compatibility date.
            exact (bool): If True, only return a schema with the exact timestamp specified in `at_or_after`. If False, return the most recent schema with a timestamp greater than `at_or_after`.

        Returns:
            The StoredSchema that matches the provided criteria.

        Raises:
            SchemaNotFoundError: If no schema matches the provided criteria.
        """
        ...

    def available_schemas(self) -> list[AvailableSchema]:
        """Return a list of available compatibility dates for schemas in the store.

        Available schemas are returned as a list of AvaliableSchema, where each instance contains:
        - compatibility_date (str): The compatibility date of the schema.
        - timestamp (int): The timestamp of the schema download.
        - datetime (str): The download date and time of the schema as an ISO 8601 string.

        Returns:
            list[AvailableSchema]: A list of available schemas in the store, sorted by
                compatibility date and then by timestamp (newest first).

        Raises:
            SchemaManagerError: If there is an error loading the schema files.
        """
        ...

    def add_schema(self, schema: EsiSchema, download_date: Instant) -> None:
        """Add a new schema to the schema store.

        This method adds a raw OpenAPI schema to the schema store along with the
        date and time when the schema was downloaded.

        Args:
            schema (EsiSchema): The EsiSchema to add to the store.
            download_date (Instant): The date and time when the schema was downloaded.

        Raises:
            SchemaManagerError: If there is an error saving the schema to the store.
            InvalidSchemaError: If the schema is invalid or cannot be processed.

        """
        ...


class CacheManagerProtocol:
    # TODO Returned CachedResponses should not have any connection to the cache data.
    # This would happen naturally with some cache implemetations, like a per file cache
    # where each CachedResponse is read from a separate file, but for in-memory caches
    # we need to make sure that the CachedResponse instances returned by get, set, and
    # refresh are copies of the data stored in the cache, to avoid unintended side effects
    # from modifying the returned CachedResponse directly. This should be called out in
    # the docstrings for these methods, and we should make sure to implement this behavior
    # in any in-memory cache implementations.

    # TODO batch writes to the cache, and provide a hot cache for recently accessed items. See Claude's suggestions for cache management strategies.
    async def __aenter__(self) -> Self:
        """Enter the runtime context related to this object."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the runtime context related to this object."""
        ...

    async def get(self, key: UUID) -> CachedResponse | None:
        """Get a cached response by cache key.

        Returned CachedResponse must be treated as immutable. If the caller needs to
        modify the CachedResponse, they should create a copy of it before making any
        modifications, to avoid unintended side effects on the cached response stored in
        the cache manager. Modifying the returned CachedResponse directly may lead to
        issues such as stale data being returned for other requests that share the same
        cache key, or inconsistencies in the cache state if the CachedResponse is updated
        with new data while it is being modified by the caller.

        Args:
            key: The UUID key for the cached response.

        Returns:
            The CachedResponse if found, or None if not found.
        """
        ...

    async def set(self, key: UUID, http_response: HttpResponse) -> CachedResponse:
        """Set a cached response in the cache.

        Returned CachedResponse must be treated as immutable. If the caller needs to
        modify the CachedResponse, they should create a copy of it before making any
        modifications, to avoid unintended side effects on the cached response stored in
        the cache manager. Modifying the returned CachedResponse directly may lead to
        issues such as stale data being returned for other requests that share the same
        cache key, or inconsistencies in the cache state if the CachedResponse is updated
        with new data while it is being modified by the caller.

        Args:
            key: The UUID key for the cached response.
            http_response: The new HttpResponse to store in the cache.

        Returns:
            The CachedResponse instance that was set in the cache.
        """
        ...

    async def refresh(
        self, key: UUID, new_http_response: HttpResponse
    ) -> CachedResponse:
        """Refresh an existing cached response with new response data.

        Returned CachedResponse must be treated as immutable. If the caller needs to
        modify the CachedResponse, they should create a copy of it before making any
        modifications, to avoid unintended side effects on the cached response stored in
        the cache manager. Modifying the returned CachedResponse directly may lead to
        issues such as stale data being returned for other requests that share the same
        cache key, or inconsistencies in the cache state if the CachedResponse is updated
        with new data while it is being modified by the caller.

        Args:
            key: The UUID key for the cached response to refresh.
            new_http_response: The new HttpResponse to update the cached response with.

        Returns:
            The updated CachedResponse instance after refreshing.

        Raises:
            KeyError: If no cached response exists for the given cache key.
        """
        ...

    async def clear(self, only_stale: bool = False) -> int:
        """Clear all cached responses from the cache.

        Args:
            only_stale: If True, only clear stale cached responses.

        Returns:
            The number of cached responses that were cleared.
        """
        ...

    async def cache_info(self) -> dict[str, Any]:
        """Get information about the cache, such as size, number of entries, etc.

        Returns:
            A dictionary containing information about the cache.
        """
        ...
