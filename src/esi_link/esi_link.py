import asyncio
import logging
from copy import deepcopy
from pathlib import Path
from types import TracebackType
from typing import Any, Optional
from uuid import NAMESPACE_URL, UUID, uuid5

import aiohttp
from aiolimiter import AsyncLimiter
from whenever import Instant

from esi_link import operation_accessors as OA
from esi_link.helpers import header_funcs as HF
from esi_link.models import (
    CachedResponse,
    CacheProtocol,
    EsiHttpProtocol,
    EsiLinkError,
    EsiLinkProtocol,
    EsiRequest,
    EsiRequests,
    EsiSchema,
    HandlerConfig,
    HandlerManagerProtocol,
    HandlerNotFoundError,
    HttpRequest,
    HttpResponse,
    InvalidHandlerError,
    ResponseContext,
    ResponseHandlerProtocol,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
ESI_LINK_NAMESPACE = uuid5(NAMESPACE_URL, "esi-link")

# ##################################################################################
# # Exceptions
# ##################################################################################


# class EsiLinkError(Exception):
#     """Base exception for ESI Link errors."""

#     pass


# class HandlerNotFoundError(EsiLinkError):
#     """Raised when a specified handler is not found."""

#     pass


# class InvalidHandlerError(EsiLinkError):
#     """Raised when a handler is invalid or cannot be instantiated."""

#     pass


# ###########################################################################
# # Models
# ###########################################################################

# # TODO make utility commands in cli to output UUID and Instant in iso format to support hand crafting Esi Requests.


# def _get_current_instant() -> Instant:
#     """Factory function to get current instant for default values.

#     This function is used as a default_factory to avoid circular dependencies
#     that can occur when using Instant.now directly in field definitions.

#     Returns:
#         Current instant in time.
#     """
#     return Instant.now()


# class HandlerConfig(BaseModel):
#     """Configuration for a response handler."""

#     name: str
#     """Name of the handler. Handler names are namespaced. The esi-link.foo namespace is reserved."""
#     config: dict[str, Any] = {}
#     """Configuration specific to the handler."""


# class AuthParams(BaseModel):
#     character_id: int
#     client_id: str
#     client_alias: str


# class EsiRequest(BaseModel):
#     """Represents a single ESI request to be executed."""

#     query_id: UUID
#     operation_id: str
#     path_parameters: dict[str, str | int | float] = {}
#     query_parameters: dict[str, str | int | float] = {}
#     auth_parameters: Optional[AuthParams] = None
#     request_body: Any = None
#     headers: dict[str, str] = {}
#     handlers: list[HandlerConfig] = []
#     """List of handler configurations to apply to this request."""


# class EsiRequests(BaseModel):
#     """Represents a batch of ESI requests to be executed."""

#     requests: dict[UUID, EsiRequest]
#     created_on: Instant = Field(default_factory=_get_current_instant)

#     def save_to_file(self, file_path: Path, overwrite: bool = False) -> None:
#         """Save the EsiRequests instance to a JSON file.

#         Args:
#             file_path: Path to the file where the JSON representation will be saved.
#             overwrite: Whether to overwrite the file if it exists. Defaults to False.
#         """
#         if file_path.is_dir():
#             raise EsiLinkError(f"{file_path} is a directory.")
#         if file_path.is_file() and not overwrite:
#             raise EsiLinkError(
#                 f"{file_path} already exists. Use overwrite=True to overwrite."
#             )
#         file_path.parent.mkdir(parents=True, exist_ok=True)
#         with open(file_path, "w") as file:
#             file.write(self.model_dump_json(indent=2))

#     @classmethod
#     def load_from_file(cls, file_path: Path) -> "EsiRequests":
#         """Load an EsiRequests instance from a JSON file.

#         Args:
#             file_path: Path to the JSON file to load.

#         Returns:
#             An instance of EsiRequests.
#         """
#         if not file_path.is_file():
#             raise EsiLinkError(f"{file_path} does not exist or is not a file.")
#         try:
#             data = file_path.read_text()
#             result = cls.model_validate_json(data)
#         except Exception as e:
#             raise EsiLinkError(
#                 f"Failed to load EsiRequests from {file_path}: {e}"
#             ) from e
#         return result


# class ResponseContext:
#     obj: dict[str, Any]


# class CachedResponse(BaseModel):
#     """Represents a cached ESI response."""

#     cache_key: UUID
#     """The cache key UUID, built from the EsiRequest."""
#     cached_on: Instant = Field(default_factory=_get_current_instant)
#     """The instant when the response was cached."""
#     response: "HttpResponse"
#     """The cached response data."""

#     def is_stale(self) -> bool:
#         """Determine if the cached response is stale.

#         This method should be implemented to check if the cached response is still valid.
#         For example, it could check the expiration time or ETag.

#         Returns:
#             True if the cached response is stale, False otherwise.
#         """
#         # Placeholder implementation; actual logic will depend on caching strategy.
#         return False


# @dataclass(slots=True)
# class IndexedOperation:
#     operation_id: str
#     method: str
#     path: str
#     operation: dict[str, Any] = field(default_factory=dict[str, Any])


# class EsiSchema(BaseModel):
#     """Represents the ESI OpenAPI schema.

#     The schema is normalized and indexed by operation ID for efficient access.
#     """

#     download_date: Instant
#     """The date the schema was downloaded."""
#     operations: dict[str, IndexedOperation] = Field(default_factory=dict)
#     """A mapping of operation IDs to IndexedOperation instances."""
#     security_schemes: dict[str, Any] = Field(default_factory=dict)
#     """A mapping of security scheme names to their definitions."""
#     info: dict[str, Any] = Field(default_factory=dict)
#     """The info section of the OpenAPI schema."""
#     openapi: str
#     """The OpenAPI version."""
#     servers: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
#     """The servers section of the OpenAPI schema."""
#     tags: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
#     """The tags section of the OpenAPI schema."""

#     @classmethod
#     def from_schema(cls, schema: dict[str, Any], download_date: Instant) -> "EsiSchema":
#         """Create an EsiSchema instance from a raw OpenAPI schema dictionary.

#         Normalizes and indexes the schema for efficient access.

#         Args:
#             schema: The OpenAPI schema as a dictionary.
#             download_date: The date the schema was downloaded.

#         Returns:
#             An instance of EsiSchema.
#         """
#         schema_copy = deepcopy(schema)
#         dereferenced_schema = resolve_internal_refs(schema_copy, schema_copy)

#         operations: dict[str, IndexedOperation] = {}
#         paths = dereferenced_schema.get("paths", {})
#         for path, methods in paths.items():
#             for method, operation in methods.items():
#                 operation_id = operation.get("operationId")
#                 if operation_id:
#                     operations[operation_id] = IndexedOperation(
#                         operation_id=operation_id,
#                         method=method.upper(),
#                         path=path,
#                         operation=operation,
#                     )
#         return cls(
#             download_date=download_date,
#             operations=operations,
#             security_schemes=dereferenced_schema.get("components", {}).get(
#                 "securitySchemes", {}
#             ),
#             info=dereferenced_schema.get("info", {}),
#             openapi=dereferenced_schema.get("openapi", ""),
#             servers=dereferenced_schema.get("servers", []),
#             tags=dereferenced_schema.get("tags", []),
#         )


# @dataclass(slots=True)
# class HttpRequest:
#     method: str
#     url: str
#     is_paged: bool
#     ctx: ResponseContext
#     esi_request: EsiRequest
#     cache_key: Optional[UUID] = None
#     """The cache key UUID, built from the EsiRequest. None if caching is not used."""
#     app_handlers: list["ResponseHandlerProtocol"] = field(
#         default_factory=list["ResponseHandlerProtocol"]
#     )
#     """App level handlers to process the response. These are run before any request level handlers."""
#     user_handlers: list["ResponseHandlerProtocol"] = field(
#         default_factory=list["ResponseHandlerProtocol"]
#     )
#     """Request level handlers to process the response. These are run after any app level handlers."""
#     headers: dict[str, str] = field(default_factory=dict[str, str])
#     """App level headers to include in the request. These are merged with any request level headers."""
#     timeout: int = 10
#     page_number: int = 0
#     """The page number for paged requests."""


# class HttpResponse(BaseModel):
#     status_code: int
#     reason: str | None
#     url: str
#     headers: tuple[tuple[str, str | None], ...]
#     json_data: Any = None
#     etag: str = ""
#     last_modified: str = ""
#     expires: str = ""
#     completed_on: Instant = Field(default_factory=_get_current_instant)


# ############################################################################
# # Protocols
# ############################################################################
# class ResponseHandlerProtocol:
#     """Protocol for handling ESI responses."""

#     async def handle_response(
#         self,
#         ctx: ResponseContext,
#         http_response: HttpResponse,
#         request: EsiRequest,
#     ) -> Any:
#         """Handle the response from an ESI request.

#         Args:
#             ctx: The response context.
#             http_response: The HttpResponse object.
#             request: The original EsiRequest object.

#         Returns:
#             The processed response data.
#         """
#         ...

#     @classmethod
#     def from_config(cls, config: HandlerConfig) -> "ResponseHandlerProtocol":
#         """Create an instance of the handler from a configuration.

#         Args:
#             config: The HandlerConfig instance containing the configuration.

#         Returns:
#             An instance of the handler.

#         Raises:
#             InvalidHandlerError: If the handler cannot be instantiated.
#         """
#         ...

#     @classmethod
#     def example_config(cls) -> tuple[HandlerConfig, str]:
#         """Return an example configuration for this handler, with a text description.

#         Example does not have to be a valid config, but should illustrate the main options.
#         """
#         ...

#     @classmethod
#     def validate_config(cls, config: HandlerConfig) -> None:
#         """Validate the handler configuration.

#         Args:
#             config: The HandlerConfig instance containing the configuration.

#         Raises:
#             InvalidHandlerError: If the configuration is invalid.
#         """
#         ...


# class HandlerManagerProtocol:
#     def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
#         """Get a handler by config.

#         Args:
#             config: The HandlerConfig instance containing the configuration.
#         Returns:
#             An instance of the handler.

#         Raises:
#             HandlerNotFoundError: If the handler is not found.
#         """
#         ...

#     def register_handler(
#         self, name: str, handler_cls: type[ResponseHandlerProtocol]
#     ) -> None:
#         """Register a handler class with a name.

#         Args:
#             name: The name of the handler.
#             handler_cls: The handler class to register.

#         Raises:
#             InvalidHandlerError: If the handler class is invalid.
#         """
#         ...


# class CacheProtocol:
#     def generate_cache_key(
#         self, esi_request: EsiRequest, esi_schema: EsiSchema
#     ) -> UUID | None:
#         """Generate a cache key for the given ESI request.

#         Args:
#             request: The EsiRequest instance for which to generate the cache key.
#             esi_schema: The EsiSchema instance representing the ESI OpenAPI schema.
#         Returns:
#             A UUID representing the cache key, or None if caching is not applicable.

#         ...
#         """
#         ...

#     def is_cached(self, cache_key: UUID) -> bool:
#         """Check if a response is cached for the given cache key.
#         Args:
#             cache_key: The UUID cache key to check.
#         Returns:
#             True if a cached response exists for the cache key, False otherwise.
#         ...
#         """
#         ...

#     def get_cached_response(self, cache_key: UUID) -> Optional[CachedResponse]:
#         """Retrieve a cached response by its cache key.

#         Args:
#             cache_key: The UUID cache key of the cached response.

#         Returns:
#             The CachedResponse instance if found, otherwise None.

#         ...
#         """
#         ...

#     def store_cached_response(self, cached_response: CachedResponse) -> None:
#         """Store a cached response.

#         Args:
#             cached_response: The CachedResponse instance to store.

#         ...
#         """
#         ...

#     def update_cached_response(
#         self, cache_key: UUID, http_response: HttpResponse
#     ) -> None:
#         """Update an existing cached response.

#         Args:
#             cached_response: The CachedResponse instance to update.

#         ...
#         """
#         ...


# class EsiLinkProtocol:
#     """Protocol for ESI Link implementations."""

#     esi_schema: EsiSchema
#     """The ESI OpenAPI schema."""
#     esi_http: "EsiHttpProtocol"
#     """The ESI HTTP client implementation."""
#     handler_manager: HandlerManagerProtocol
#     """The handler manager for response handlers."""

#     async def execute_requests(
#         self,
#         ctx: ResponseContext,
#         requests: EsiRequests,
#     ) -> None:
#         """Execute a batch of ESI requests.

#         Args:
#             requests: The EsiRequests instance containing the requests to execute.
#             session: An optional aiohttp ClientSession to use for the requests.
#             response_handler: An optional ResponseHandlerProtocol to process responses.

#         Returns:
#             A dictionary mapping request UUIDs to their responses.
#         """
#         ...


# class EsiHttpProtocol:
#     """Protocol for ESI HTTP client implementations."""

#     session: aiohttp.ClientSession | None
#     cache: CacheProtocol
#     esi_schema: EsiSchema

#     async def __aenter__(self) -> "EsiHttpRateLimited": ...

#     async def __aexit__(
#         self,
#         exc_type: type[BaseException] | None,
#         exc: BaseException | None,
#         tb: TracebackType | None,
#     ) -> None: ...

#     async def execute_requests(
#         self,
#         requests: list[HttpRequest],
#     ) -> list[tuple[HttpRequest, None | BaseException]]:
#         """Execute a list of HTTP requests.

#         Args:
#             requests: A list of HttpRequest instances to execute.

#         Returns:
#             A list of tuples containing the HttpRequest and either None or an exception if one occurred.
#         """
#         ...


###########################################################################
# Helpers
###########################################################################
def build_url(
    esi_request: EsiRequest,
    esi_schema: EsiSchema,
    base_url: str = "",
) -> str:
    """Build the full URL for an ESI request using the ESI schema.

    Args:
        esi_request: The EsiRequest instance containing the operation ID and parameters.
        esi_schema: The EsiSchema instance containing the OpenAPI schema.

    Returns:
        The full URL as a string.
    """
    operation = esi_schema.operations.get(esi_request.operation_id)
    base_url = base_url or esi_schema.servers[0]["url"]
    if not operation:
        raise EsiLinkError(f"Operation ID not found: {esi_request.operation_id}")
    path_params = esi_request.path_parameters or {}
    query_params = esi_request.query_parameters or {}
    path_template = operation.path
    path = path_template.format(**path_params)
    resolved_url = f"{base_url.strip('/')}/{path.strip('/')}"
    # Construct the query string from the query parameters
    # Sort keys so URL is stable regardless of dict insertion order
    query_items = sorted(query_params.items(), key=lambda kv: kv[0])
    query_string = "&".join([f"{key}={value}" for key, value in query_items])
    # Combine the path and query string into the final URL
    return f"{resolved_url}?{query_string}" if query_string else resolved_url


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


###########################################################################
# Implementations
###########################################################################

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


###########################################################################
# EsiHttpProtocol Implementations
###########################################################################


class EsiHttpRateLimited(EsiHttpProtocol):
    """An ESI HTTP client implementation that collects requests and processes them asynchronously."""

    def __init__(
        self,
        cache: CacheProtocol,
        esi_schema: EsiSchema,
        max_rate: int = 100,
        time_period: int = 60,
    ) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.cache = cache
        self.esi_schema = esi_schema
        self.max_rate = max_rate
        self.time_period = time_period

    async def __aenter__(self) -> "EsiHttpRateLimited":
        if not self.session:
            self.session = aiohttp.ClientSession()
        self.limiter = AsyncLimiter(self.max_rate, self.time_period)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self.session is not None, "Session is not initialized."
        await self.session.close()

    async def _do_handlers(
        self, request: HttpRequest, http_response: HttpResponse
    ) -> None:
        # Process app level handlers
        for handler in request.app_handlers:
            await handler.handle_response(
                request.ctx, http_response, request.esi_request
            )
        # Process user level handlers
        for handler in request.user_handlers:
            await handler.handle_response(
                request.ctx, http_response, request.esi_request
            )

    async def _worker(
        self, request: HttpRequest
    ) -> tuple[HttpRequest, BaseException | None]:
        """Worker to process a single HTTP request.

        Args:
            request: The HttpRequest instance to process.

        Returns:
            A tuple of the HttpRequest and either None or an exception if one occurred.
        """
        try:
            if not self.session:
                raise EsiLinkError("HTTP session is not initialized.")
            if request.cache_key is not None:
                cached_response = self.cache.get_cached_response(request.cache_key)
                if cached_response is not None and not cached_response.is_stale():
                    await self._do_handlers(request, cached_response.response)
                    return (request, None)
                if cached_response is not None and cached_response.is_stale():
                    # Add conditional headers to the request
                    # Use ETag and Last-Modified from the cached response
                    if cached_response.response.etag:
                        request.headers["If-None-Match"] = cached_response.response.etag
                    if cached_response.response.last_modified:
                        request.headers["If-Modified-Since"] = (
                            cached_response.response.last_modified
                        )
            _, http_response = await self.get_response(request=request)
            match http_response.status_code:
                case 200:
                    if request.is_paged:
                        await self.get_paged_data(
                            request=request, first_page=http_response
                        )
                    if request.cache_key is not None:
                        cached_response = CachedResponse(
                            cache_key=request.cache_key, response=http_response
                        )
                        self.cache.store_cached_response(cached_response)
                    await self._do_handlers(request, http_response)
                    return (request, None)
                case 201:  # Created Successful
                    # TODO handle 201 Created responses if needed
                    await self._do_handlers(request, http_response)
                    return (request, None)
                case 204:  # No Content Successful
                    # TODO handle 204 No Content responses if needed
                    await self._do_handlers(request, http_response)
                    return (request, None)
                case 304:
                    if request.cache_key is None:
                        raise EsiLinkError("Received 304 but no cache is configured.")
                    self.cache.update_cached_response(request.cache_key, http_response)
                    cached_response = self.cache.get_cached_response(request.cache_key)
                    if cached_response is None:
                        raise EsiLinkError("Received 304 but no cached response found.")
                    await self._do_handlers(request, cached_response.response)
                    return (request, None)
                case 429:  # Rate Limited
                    # TODO consider retry logic here.
                    retry_after = HF.retry_after(http_response.headers)
                    raise EsiLinkError(
                        f"Rate limited on request to {http_response.url}. Retry after {retry_after} seconds."
                    )

                # TODO handle other status codes
                case _:
                    logger.warning(
                        f"Unhandled status code {http_response.status_code} for URL {http_response.url}"
                    )
                    # TODO more specific error with code and reason as fields.
                    raise EsiLinkError(
                        f"Unhandled status code {http_response.status_code}, {http_response.reason} for URL {http_response.url}"
                    )
        except Exception as e:
            logger.error(f"Error processing request for URL {request.url}: {e}")
            return (request, e)

    async def get_paged_data(
        self, request: HttpRequest, first_page: HttpResponse
    ) -> None:
        """Complete a paged request by fetching all pages."""
        paged_requests = self.build_paged_requests(request, first_page)
        tasks = [self.get_response(req) for req in paged_requests]
        results = await asyncio.gather(*tasks)
        for result in results:
            _, http_response = result
            if http_response.status_code != 200:
                raise EsiLinkError(
                    f"Failed to fetch paged data for URL {http_response.url} with status code {http_response.status_code}"
                )
            if first_page.etag and http_response.etag != first_page.etag:
                raise EsiLinkError(
                    f"ETag mismatch for paged response at URL {http_response.url}"
                )
            # Merge the JSON data from the paged response into the first page
            if isinstance(first_page.json_data, list) and isinstance(  # pyright: ignore[reportUnknownMemberType]
                http_response.json_data, list
            ):
                first_page.json_data.extend(http_response.json_data)  # pyright: ignore[reportUnknownMemberType]
            elif isinstance(first_page.json_data, dict) and isinstance(  # pyright: ignore[reportUnknownMemberType]
                http_response.json_data, dict
            ):
                first_page.json_data.update(http_response.json_data)  # pyright: ignore[reportUnknownMemberType]
            else:
                logger.warning(
                    f"Cannot merge paged response data for URL {http_response.url}"
                )
        # After all pages are fetched and merged, run handlers on the combined response
        await self._do_handlers(request, first_page)
        return None

    def build_paged_requests(
        self, request: HttpRequest, first_page: HttpResponse
    ) -> list[HttpRequest]:
        """Build a list of paged requests based on the first page response."""

        if not request.is_paged:
            raise EsiLinkError("Request is not marked as paged.")
        page_count = HF.pages_available(first_page.headers)
        if page_count < 1:
            raise EsiLinkError("Invalid page count retrieved from headers.")
        http_requests: list[HttpRequest] = []
        if page_count == 1:
            return http_requests
        for page_number in range(2, page_count + 1):
            paged_request = deepcopy(request)
            # Clear any user defined handlers for paged requests
            paged_request.esi_request.handlers = []
            paged_request.page_number = page_number
            # Update the URL to include the page parameter
            paged_request.esi_request.query_parameters["page"] = page_number
            paged_request.url = build_url(
                paged_request.esi_request,
                esi_schema=self.esi_schema,
            )
            http_requests.append(paged_request)
        return http_requests

    async def get_response(
        self, request: HttpRequest
    ) -> tuple[HttpRequest, HttpResponse]:
        """Get a single HTTP response.

        Args:
            request: The HttpRequest instance to execute.

        Returns:
            A tuple of the HttpRequest and HttpResponse.
        """
        if not self.session:
            raise EsiLinkError("HTTP session is not initialized.")
        async with self.limiter:
            timeout_obj = aiohttp.ClientTimeout(total=request.timeout)
            async with self.session.request(
                method=request.method,
                url=request.url,
                headers=request.headers,
                timeout=timeout_obj,
            ) as response:
                http_response = HttpResponse(
                    status_code=response.status,
                    reason=response.reason,
                    url=str(response.url),
                    headers=tuple(response.headers.items()),
                    json_data=await response.json(),
                    etag=response.headers.get("ETag", ""),
                    last_modified=response.headers.get("Last-Modified", ""),
                    expires=response.headers.get("Expires", ""),
                )
                return (request, http_response)

    async def execute_requests(
        self,
        requests: list[HttpRequest],
    ) -> list[tuple[HttpRequest, BaseException | None]]:
        """Execute a list of HTTP requests.

        Args:
            requests: A list of HttpRequest instances to execute.
        Returns:
            A list of tuples containing the HttpRequest and either None or an exception if one occurred.
        """

        tasks = [self._worker(req) for req in requests]
        results = await asyncio.gather(*tasks)
        return results


###########################################################################
# EsiLinkProtocol Implementations
###########################################################################


class EsiLink(EsiLinkProtocol):
    """Default implementation of the EsiLinkProtocol.

    This implementation uses aiohttp to execute ESI requests and process responses.
    """

    def __init__(
        self,
        esi_schema: EsiSchema,
        esi_http: EsiHttpProtocol,
        handler_manager: HandlerManagerProtocol,
    ) -> None:
        self.esi_schema = esi_schema
        self.esi_http = esi_http
        self.handler_manager = handler_manager

        app_handler_configs = self.app_handler_configs()
        self.app_handlers: list[ResponseHandlerProtocol] = self.init_handlers(
            app_handler_configs
        )

    def app_handler_configs(self) -> list[HandlerConfig]:
        """Get the application-level handler configurations.

        This method should be implemented to return the list of HandlerConfig
        instances that define the application-level response handlers.

        Returns:
            A list of HandlerConfig instances.
        """
        # TODO define a list of app handler configs.
        return []

    def init_handlers(
        self, handler_configs: list[HandlerConfig]
    ) -> list[ResponseHandlerProtocol]:
        """Initialize application-level response handlers."""

        app_handlers = [
            self.handler_manager.get_handler(config) for config in handler_configs
        ]
        return app_handlers

    async def execute_requests(
        self,
        ctx: ResponseContext,
        requests: EsiRequests,
    ) -> None:
        # Build HttpRequest objects from EsiRequest objects
        http_requests: list[HttpRequest] = []
        for req in requests.requests.values():
            url = build_url(req, self.esi_schema)
            user_handlers = self.init_handlers(req.handlers)
            is_paged = False  # FIXME implement is_paged check
            indexed_operation = self.esi_schema.operations.get(req.operation_id)
            if not indexed_operation:
                raise EsiLinkError(f"Operation ID not found: {req.operation_id}")
            http_request = HttpRequest(
                method=indexed_operation.method,
                url=url,
                ctx=ctx,
                esi_request=req,
                cache_key=self.esi_http.cache.generate_cache_key(
                    esi_request=req, esi_schema=self.esi_schema
                ),
                app_handlers=self.app_handlers,
                user_handlers=user_handlers,
                headers=req.headers,
                is_paged=is_paged,
            )
            http_requests.append(http_request)
            async with self.esi_http as http_client:
                await http_client.execute_requests(http_requests)
        return None


###########################################################################
# ResponseHandlerProtocol Implementations
###########################################################################


class JsonFileResponseHandler(ResponseHandlerProtocol):
    """A response handler that saves the JSON response to a file."""

    name: str = "esi-link.json_data_file"

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    async def handle_response(
        self,
        ctx: ResponseContext,
        http_response: HttpResponse,
        request: EsiRequest,
    ) -> None:
        if http_response.json_data is not None:
            path_out = Path(self._file_path.format(**self.tokens(request)))
            path_out.parent.mkdir(parents=True, exist_ok=True)
            with open(path_out, "w") as file:
                import json

                json.dump(http_response.json_data, file, indent=2)

    def tokens(self, request: EsiRequest) -> dict[str, str]:
        token_values = {
            "operation_id": request.operation_id,
            "query_id": str(request.query_id),
            "now": Instant.now().format_iso(),
        }
        token_values.update(
            {key: str(value) for key, value in request.path_parameters.items()}
        )
        token_values.update(
            {key: str(value) for key, value in request.query_parameters.items()}
        )
        if request.auth_parameters:
            token_values.update(
                {
                    "character_id": str(request.auth_parameters.character_id),
                    "client_id": str(request.auth_parameters.client_id),
                    "client_alias": request.auth_parameters.client_alias,
                }
            )
        return token_values

    @classmethod
    def from_config(cls, config: HandlerConfig) -> "JsonFileResponseHandler":
        file_path_str = config.config.get("file_path")
        if not file_path_str:
            raise InvalidHandlerError("file_path is required in handler config.")
        return cls(file_path=file_path_str)

    @classmethod
    def example_config(cls) -> tuple[HandlerConfig, str]:
        """Return an example configuration for this handler, with a text description.

        Example does not have to be a valid config, but should illustrate the main options.
        """
        example = HandlerConfig(
            name=cls.name,
            config={"file_path": "responses/{operation_id}-response.json"},
        )
        description = (
            "Saves the JSON response to the specified file path. "
            "The file_path option is required. file_path supports str.format replacement "
            "with tokens for operation_id, query_id, now, and any path, query or auth parameters."
        )
        return example, description

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        if "file_path" not in config.config:
            raise InvalidHandlerError("file_path is required in handler config.")
        if not config.name.startswith("esi-link."):
            raise InvalidHandlerError(
                "Handler name must be in the 'esi-link.' namespace."
            )


class HandlerManager(HandlerManagerProtocol):
    """A simple handler manager implementation."""

    def __init__(self) -> None:
        self.handlers: dict[str, type[ResponseHandlerProtocol]] = {}

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        handler_cls = self.handlers.get(config.name)
        if not handler_cls:
            raise HandlerNotFoundError(f"Handler not found: {config.name}")
        return handler_cls.from_config(config)

    def register_handler(
        self, name: str, handler_cls: type[ResponseHandlerProtocol]
    ) -> None:
        if not issubclass(handler_cls, ResponseHandlerProtocol):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise InvalidHandlerError(
                f"Handler class must implement ResponseHandlerProtocol: {name}"
            )
        self.handlers[name] = handler_cls


class LinkManager:
    """Handles the initialization and management of EsiLink instances."""

    def __init__(
        self,
        esi_schema: dict[str, Any],
        schema_download_date: Instant,
    ) -> None:
        self.esi_schema = EsiSchema.from_schema(
            schema=esi_schema, download_date=schema_download_date
        )
        self._handler_manager = self.get_handler_manager()

    def get_handler_manager(self) -> HandlerManagerProtocol:
        handler_manager = HandlerManager()
        handler_manager.register_handler(
            JsonFileResponseHandler.name, JsonFileResponseHandler
        )
        return handler_manager

    def esi_link_factory(self) -> EsiLinkProtocol:
        cache = InMemoryCache()
        esi_http = EsiHttpRateLimited(cache=cache, esi_schema=self.esi_schema)
        esi_link = EsiLink(
            esi_schema=self.esi_schema,
            esi_http=esi_http,
            handler_manager=self._handler_manager,
        )
        return esi_link
