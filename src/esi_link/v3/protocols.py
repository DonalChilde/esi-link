"""Protocols for ESI Link."""

from types import TracebackType
from typing import Any, ClassVar, Protocol, Self
from uuid import UUID

import aiohttp
from whenever import Instant

from esi_link.v3.models import (
    CachedResponse,
    CachedResponseStatus,
    GeneratedUrlInfo,
    HttpResponse,
    IndexedEsiSchema,
    Request,
    RequestGroup,
    Response,
    ResponseGroup,
    ResponseGroupHandlerConfig,
    ResponseHandlerConfig,
    RuntimeGroupInfo,
    RuntimeRequest,
    RuntimeRequestInfo,
)


class HttpRequestExecutorProtocol(Protocol):
    async def __call__(
        self,
        request: RuntimeRequest,
        session: aiohttp.ClientSession,
    ) -> Response:
        """Protocol for executing RuntimeRequests.

        Rate limit management is left to the implementing class, to allow for flexibility
        in how rate limiting is handled.
        """
        ...


class RuntimeRequestInfoGeneratorProtocol(Protocol):
    async def __call__(self, request: Request) -> RuntimeRequestInfo: ...


class RuntimeGroupInfoGeneratorProtocol(Protocol):
    def __call__(self, request_group: RequestGroup) -> RuntimeGroupInfo: ...


class RequestValidatorProtocol(Protocol):
    async def __call__(self, request: Request) -> None:
        """Validate a request.

        Raises:
            RequestValidationError
        """
        ...


class RequestGroupExecutorProtocol(Protocol):
    request_executor: HttpRequestExecutorProtocol | None
    runtime_info: RuntimeRequestInfoGeneratorProtocol | None
    request_validator: RequestValidatorProtocol | None

    async def __call__(self, request_group: RequestGroup) -> ResponseGroup:
        """Execute a RequestGroup and return a ResponseGroup.

        This function should handle the entire lifecycle of executing a RequestGroup,
        including generating RuntimeRequests from the Requests in the group, validating
        the Requests, executing the RuntimeRequests, and handling the Responses to produce
        the final ResponseGroup.
        """
        ...


class RequestGroupValidatorProtocol(Protocol):
    def __call__(self, request_group: RequestGroup) -> None:
        """Validate a RequestGroup.

        Raises:
            RequestValidationError
        """
        ...


class ResponseHandlerProtocol(Protocol):
    name: ClassVar[str]
    config: ResponseHandlerConfig

    async def __call__(self, response: Response) -> Response:
        """Handle a response.

        This can be used for things like error handling, response transformation,
        persisting responses to disk, etc.

        Args:
            response: The response to handle.

        Returns:
            The handled response.

        Raises:
            ResponseHandlingError: If an error occurs while handling the response.
        """
        ...

    @classmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        """Factory method to create a handler instance from a ResponseHandlerConfig.

        The config should be validated before creating the handler instance.


        Args:
            config: The ResponseHandlerConfig instance containing the configuration for the handler.

        Raises:
            InvalidHandlerError: If the configuration is invalid for this handler.
        """
        raise NotImplementedError("from_config method must be implemented by subclass")

    @classmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        """Validate a ResponseHandlerConfig for this handler.

        This method should be called before creating a handler instance from a config,
        to ensure that the values in the config are valid for this handler.

        This is only required to validate the presence of the required config values,
        and that they are of the correct type. The actual values might not be valid until
        runtime, e.g., if the config includes a reference to a value in the EsiResponse
        that is not present until the response is received.

        Args:
            config: The ResponseHandlerConfig instance to validate.

        Raises:
            InvalidHandlerConfigError: If the configuration is invalid for this handler.
        """
        raise NotImplementedError(
            "validate_config method must be implemented by subclass"
        )


class ResponseHandlerManagerProtocol(Protocol):
    def get_handler(
        self, config: ResponseHandlerConfig
    ) -> ResponseHandlerProtocol | None:
        """Get a handler by config.

        Args:
            config: The HandlerConfig instance containing the configuration.

        Returns:
            An instance of the handler or None if the handler is not found.

        Raises:
            InvalidHandlerConfigError: If the config is invalid for the specified handler.
        """
        raise NotImplementedError("get_handler method must be implemented by subclass")

    def register_handler(self, handler_cls: type[ResponseHandlerProtocol]) -> None:
        """Register a handler class by its name.

        Args:
            handler_cls: The handler class to register.

        Raises:
            InvalidHandlerConfigError: If the handler class is invalid.
        """
        raise NotImplementedError(
            "register_handler method must be implemented by subclass"
        )

    def registered_handlers(self) -> dict[str, type[ResponseHandlerProtocol]]:
        """Get a dictionary of registered handler classes by their names.

        Returns:
            A dictionary mapping handler names to their corresponding handler classes.
        """
        raise NotImplementedError(
            "registered_handlers method must be implemented by subclass"
        )

    def validate_handler_config(self, config: ResponseHandlerConfig) -> None:
        """Validate a handler configuration against the registered handler.

        Args:
            config: The ResponseHandlerConfig instance containing the configuration.

        Raises:
            InvalidHandlerConfigError: If the configuration is invalid for the specified handler.
            HandlerNotFoundError: If the specified handler is not found.
        """
        raise NotImplementedError(
            "validate_handler_config method must be implemented by subclass"
        )


class ResponseGroupHandlerProtocol(Protocol):
    name: ClassVar[str]
    config: ResponseGroupHandlerConfig

    async def __call__(
        self, request_group: RequestGroup, responses: list[Response]
    ) -> list[Response]: ...
    @classmethod
    def from_config(cls, config: ResponseGroupHandlerConfig) -> Self: ...
    @classmethod
    def validate_config(cls, config: ResponseGroupHandlerConfig) -> None: ...


class ResponseGroupHandlerManagerProtocol(Protocol):
    def get_handler(
        self, config: ResponseGroupHandlerConfig
    ) -> ResponseGroupHandlerProtocol: ...
    def register_handler(
        self, handler_cls: type[ResponseGroupHandlerProtocol]
    ) -> None: ...
    def registered_handlers(self) -> dict[str, type[ResponseGroupHandlerProtocol]]: ...
    def validate_handler_config(self, config: ResponseGroupHandlerConfig) -> None: ...


class CacheManagerProtocol:
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
        ...

    def get(
        self, key: UUID, local_max_age: int | None = None
    ) -> tuple[CachedResponse | None, CachedResponseStatus]:
        """Get a cached response by cache key.

        Local max age allows the caller to specify a max age for staleness that is
        different from the max age received from the server.

        Returned CachedResponse must be treated as immutable. If the caller needs to
        modify the CachedResponse, they should create a copy of it before making any
        modifications, to avoid unintended side effects on the cached response stored in
        the cache manager. Modifying the returned CachedResponse directly may lead to
        issues such as stale data being returned for other requests that share the same
        cache key, or inconsistencies in the cache state if the CachedResponse is updated
        with new data while it is being modified by the caller.

        Args:
            key: The UUID key for the cached response.
            local_max_age: The maximum age of the cached response in seconds. If the cached
                response is older than this, it will be considered stale.

        Returns:
            A tuple containing the CachedResponse if found, or None if not found, and
                the CachedResponseStatus.
        """
        ...

    def set(self, key: UUID, http_response: HttpResponse) -> CachedResponse:
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

    def refresh(self, key: UUID, new_http_response: HttpResponse) -> CachedResponse:
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

    def clear(self, only_stale: bool = False) -> int:
        """Clear all cached responses from the cache.

        Args:
            only_stale: If True, only clear stale cached responses.

        Returns:
            The number of cached responses that were cleared.
        """
        ...

    def cache_info(self) -> dict[str, Any]:
        """Get information about the cache, such as size, number of entries, etc.

        Returns:
            A dictionary containing information about the cache.
        """
        ...


class CacheFactoryProtocol:
    def __call__(
        self, cache_name: str, cache_config: dict[str, Any]
    ) -> CacheManagerProtocol:
        """Factory protocol for creating CacheManagerProtocol instances.

        Args:
            cache_name: The name of the cache to create.
            cache_config: A dictionary of configuration options for the cache.

        Returns:
            An instance of CacheManagerProtocol.

        Raises:
            ValueError: If the cache cannot be created with the given name and configuration.

        """
        ...


class UrlGeneratorProtocol:
    def generate_path_url(self, request: Request, schema: IndexedEsiSchema) -> str:
        """Generate the url path for an ESI request based on its parameters.\

        This url does not contain query parameters, and is not suitable for generateing
        a cache key. It is used as the url argument for http requests, assuming that
        query parameters are sent separately.
        """
        ...

    def generate_cache_url(self, request: Request, schema: IndexedEsiSchema) -> str:
        """Generate the url to use for cache key generation for an ESI request based on its parameters.

        This url should contain all path and most query parameters, and should be
        consistent for requests that should share a cache key. It is used for generating
        cache keys, and is not necessarily the same as the url used for making the http request.

        NOTE: Validate the request before generating the cache url, to ensure that all
        required parameters are present and correctly formatted, to avoid generating
        different cache urls for requests that should share a cache key.
        """
        ...

    def generate_cache_key(self, request: Request, schema: IndexedEsiSchema) -> UUID:
        """Generate a cache key for an ESI request based on its parameters.

        The key is usually generated by hashing the url generated by generate_cache_url,
        but can be any UUID that is consistently generated for requests that should share
        a cache key.
        """
        ...

    def __call__(self, request: Request, schema: IndexedEsiSchema) -> GeneratedUrlInfo:
        """Generate all url related information for an ESI request.

        This is a convenience method that generates the path url, cache url, and cache key
        for an ESI request in one call, since these values are often needed together
        and share intermediate calculations.

        NOTE: Validate the request before generating the cache url, to ensure that all
        required parameters are present and correctly formatted, to avoid generating
        different cache urls for requests that should share a cache key.
        """
        ...


class SchemaManagerProtocol:
    """Protocol for managing ESI schemas, including storing, retrieving, and adding schemas to the schema store.

    While the Esi schema is versioned by its compatibility date, minor changes do not
    trigger an update of the compatibility date. This means that multiple versions of
    the schema can exist for the same compatibility date.

    To avoid ambiguity when multiple versions of the schema exist for the same compatibility date,
    schemas in the store are indexed by both their compatibility date and their download
    timestamp, to allow for retrieval of specific versions of the schema.
    """

    def get_schema_for_date(
        self, compatibility_date: str, timestamp: int
    ) -> IndexedEsiSchema:
        """Get the ESI schema corresponding to the given compatibility date and timestamp.

        Args:
            compatibility_date (str): The compatibility date of the schema to retrieve.
            timestamp (int): The timestamp of the schema to retrieve.

        Returns:
            IndexedEsiSchema: The ESI schema corresponding to the given compatibility date and timestamp.

        Raises:
            SchemaNotFoundError: If no schema is found for the given compatibility date and timestamp.
            SchemaManagerError: If there is an error loading the schema file.
        """
        ...

    def get_latest_schema(self, compatibility_date: str | None) -> IndexedEsiSchema:
        """Get the latest ESI schema available in the schema store.

        If compatibility_date is provided, return the latest schema for that compatibility date.
        If compatibility_date is None, return the latest schema across all compatibility dates.

        Args:
            compatibility_date (str | None): The compatibility date to filter schemas by,
                or None to get the latest schema across all compatibility dates.

        Returns:
            IndexedEsiSchema: The latest ESI schema available in the schema store.

        Raises:
            SchemaNotFoundError: If no schemas are found in the schema store.
            SchemaManagerError: If there is an error loading the schema files.
        """
        ...

    def available_schemas(self) -> list[tuple[str, int, str]]:
        """Return a list of available compatibility dates for schemas in the store.

        Available schemas are returned as a list of tuples, where each tuple contains:
        - compatibility_date (str): The compatibility date of the schema.
        - timestamp (int): The timestamp of the schema download.
        - datetime (str): The download date and time of the schema as an ISO 8601 string.

        Returns:
            list[tuple[str, int, str]]: A list of available schemas in the store.

        Raises:
            SchemaManagerError: If there is an error loading the schema files.
        """
        ...

    def add_schema(self, schema: dict[str, Any], download_date: Instant) -> None:
        """Add a new schema to the schema store.

        This method adds a raw OpenAPI schema to the schema store along with the
        date and time when the schema was downloaded.

        Args:
            schema (dict[str, Any]): The raw OpenAPI schema to add to the store.
            download_date (Instant): The date and time when the schema was downloaded.

        Raises:
            SchemaManagerError: If there is an error saving the schema to the store.
            InvalidSchemaError: If the schema is invalid or cannot be processed.

        """
        ...


# class AuthenticationHeaderProviderProtocol(Protocol):
#     async def header(self, character_id: int) -> dict[str, str] | None:
#         """Return the authentication header to be included in ESI requests.

#         Args:
#             character_id: The ID of the character for whom to generate the authentication header.

#         Returns:
#             A dictionary containing the authentication header, or None if no
#                 authentication is available.
#         """
#         ...
