"""Models for ESI Link."""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from types import TracebackType
from typing import Annotated, Any, ClassVar, Literal, Protocol, Self, cast
from uuid import UUID, uuid4

import aiohttp
from pydantic import BaseModel, ConfigDict, Field, SkipValidation
from whenever import Instant

from esi_link.v3.type_defs import Lang


def _get_current_instant() -> Instant:
    """Factory function to get current instant for default values.

    This function is used as a default_factory to avoid circular dependencies
    that can occur when using Instant.now directly in field definitions.

    Returns:
        Current instant in time.
    """
    return Instant.now()


class CachedResponseStatus(StrEnum):
    HIT = "HIT"
    MISS = "MISS"
    STALE = "STALE"


class CacheAction(StrEnum):
    ADDED_TO_CACHE = "ADDED_TO_CACHE"
    CACHED_RESPONSE_USED = "CACHED_RESPONSE_USED"
    CACHE_304_REFRESH = "CACHE_304_REFRESH"


@dataclass(slots=True)
class SchemaDownload:
    """A class representing a downloaded ESI schema and its associated metadata."""

    raw_schema: dict[str, Any]
    download_date: Instant


class ResponseHandlerConfig(BaseModel):
    """Configuration for a response handler.

    Handler names are namespaced, with the format <namespace>:<handler_name>. Namespaces
    are case insensitive, so "esi-link" and "ESI-LINK" would be considered the same
    namespace. The esi-link namespace is reserved for built-in handlers,
    e.g., esi-link:BuiltinHandler. Custom handlers should use a different namespace to
    avoid conflicts. For example, a handler named "my_handler" could be registered under
    the name "my_namespace.my_handler" to avoid conflicts with any built-in handlers or
    other custom handlers that may be registered in the future.

    Runtime values for handlers can be included in the config dictionary, and will be
    passed to the handler when it is initialized. e.g. {"my_namespace.my_parameter": "value"}

    It is the responsibility of the handler implementation to parse the config and
    extract any needed values from it. The config dictionary is not interpreted by the
    core ESI Link code, and is validated only by the handler implementation.

    Example:
    ```python
    ResponseHandlerConfig(
        name="my_namespace.my_handler",
        config={
            "type_id": "EsiRequest.query_parameters.type_id",
            "download_date": "EsiResponse.http_response.date",
        },
    )
    ```
    """

    name: str
    """Name of the handler."""
    config: dict[str, Any] = {}
    """Configuration specific to the handler."""


class ResponseGroupHandlerConfig(BaseModel):
    """Configuration for a response handler that operates on a group of responses.

    This is similar to ResponseHandlerConfig, but is intended for handlers that need to
    operate on a group of responses together, e.g. to aggregate data across multiple
    responses. The handler will receive the entire ResponseGroup as input, and can
    access the individual responses and their associated requests and runtime info as
    needed.

    Example:
    ```python
    ResponseGroupHandlerConfig(
        name="my_namespace.my_group_handler",
        config={
            "type_id": "ResponseGroup.request_group.requests.*.query_parameters.type_id",
            "download_date": "ResponseGroup.responses.*.http_response.date",
        },
    )
    ```
    """

    name: str
    """Name of the handler."""
    config: dict[str, Any] = {}
    """Configuration specific to the handler."""


class RuntimeRequestInfo(BaseModel):
    """Represents the runtime information needed for a Request."""

    path_url: str
    additional_query_params: dict[str, str] = Field(default_factory=dict)
    """Additional query parameters that are not defined in the request, but are needed 
    for the request. Including things like the page number for paged requests."""
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    is_paged: bool = False
    is_auth: bool = False
    headers: dict[str, str] = {}
    """Includes UserAgent, If-None-Match, If-Modified-Since, X-Compatibility-Date, and auth if required."""
    timeout: int = 10
    cache_key: UUID | None = None
    """Cache key for the request, if applicable. This is used to identify cached responses. Paged requests only have a cache key for the first page."""
    response_handlers: Annotated[
        list["ResponseHandlerProtocol"], Field(..., exclude=True), SkipValidation
    ]
    """The list of response handler instances to run for this request, in the order they should be run."""
    metrics: "RequestMetrics"
    parent_id: UUID | None = None
    """The request_id of the parent request if this request is a sub-request, e.g. a paged request or a retry."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RuntimeGroupInfo(BaseModel):
    """Represents the runtime information for a group of ESI requests."""

    metrics: "RequestGroupMetrics"
    response_group_handlers: list[Any] = Field(..., exclude=True)
    """The list of response group handler instances to run for this group of requests, in the order they should be run."""


class Request(BaseModel):
    """Represents a single ESI request to be executed."""

    request_id: UUID = Field(default_factory=uuid4)
    operation_id: str
    path_parameters: dict[str, str | int | float] = {}
    query_parameters: dict[str, str | int | float] = {}
    auth_character_id: int | None = None
    lang: Lang = "en"
    json_body: Any | None = None
    response_handlers: list[ResponseHandlerConfig] = []


class RuntimeRequest(BaseModel):
    request: Request
    runtime_info: RuntimeRequestInfo


class RequestGroup(BaseModel):
    """Represents a batch of ESI requests to be executed.

    This model exists mostly for serialization puposes, with the imagined use being
    a set of requests that are loaded from disk and run repeatedly over time. For instance,
    downloading a fresh set of pricing data every day.
    """

    created_on: Instant = Field(default_factory=_get_current_instant)
    group_id: UUID
    description: str = ""
    requests: dict[UUID, Request]
    response_group_handlers: list[ResponseGroupHandlerConfig] = []


@dataclass(slots=True)
class X_ratelimit:
    group: str
    limit: str
    remaining: str
    used: str


class HttpResponse(BaseModel):
    """Represents the data of an ESI response."""

    status_code: int
    url: str
    headers: dict[str, str] = {}
    body_text: str
    received_at: Instant = Field(default_factory=_get_current_instant)

    @property
    def etag(self) -> str | None:
        """Extract the ETag from the response headers, if present."""
        return (
            self.headers.get("ETag")
            or self.headers.get("Etag")
            or self.headers.get("etag")
        )

    @property
    def last_modified(self) -> str | None:
        """Extract the Last-Modified header from the response headers, if present."""
        return (
            self.headers.get("Last-Modified")
            or self.headers.get("Last-modified")
            or self.headers.get("last-modified")
        )

    @property
    def expires(self) -> str | None:
        """Extract the Expires header from the response headers, if present."""
        return self.headers.get("Expires") or self.headers.get("expires")

    @property
    def date(self) -> str | None:
        """Extract the Date header from the response headers, if present."""
        return self.headers.get("Date") or self.headers.get("date")

    @property
    def cache_control(self) -> str | None:
        """Extract the Cache-Control header from the response headers, if present."""
        return (
            self.headers.get("Cache-Control")
            or self.headers.get("Cache-control")
            or self.headers.get("cache-control")
        )

    @property
    def max_age(self) -> int | None:
        """Extract the max-age directive from the Cache-Control header, if present."""
        cache_control = self.cache_control
        if cache_control:
            directives = cache_control.split(",")
            for directive in directives:
                if "max-age" in directive:
                    try:
                        return int(directive.split("=")[1].strip())
                    except (IndexError, ValueError):
                        pass
        return None

    @property
    def expires_at(self) -> Instant | None:
        """Calculate the expiration time of the response based on the Expires header or Cache-Control max-age."""
        max_age = self.max_age
        if max_age is not None:
            return self.received_at.add(seconds=max_age)
        if self.expires:
            try:
                return Instant.parse_rfc2822(self.expires)
            except ValueError:
                pass
        return None

    @property
    def pages(self) -> int:
        """Extract the number of pages from the X-Pages header, if present."""
        pages = self.headers.get("X-Pages", 1) or self.headers.get("x-pages", 1)
        return int(pages)

    @property
    def body_json(self) -> Any | None:
        """Parse the body text as JSON, if possible.

        Returns:
            The parsed JSON object, or None if parsing fails.
        """
        try:
            return json.loads(self.body_text)
        except ValueError:
            return None

    @property
    def ratelimit(self) -> X_ratelimit | None:
        """Extract the rate limit information from the X-RateLimit headers, if present."""
        group = self.headers.get("X-Ratelimit-Group", "unknown")
        limit = self.headers.get("X-Ratelimit-Limit", "unknown")
        remaining = self.headers.get("X-Ratelimit-Remaining", "unknown")
        used = self.headers.get("X-Ratelimit-Used", "unknown")
        # if any(value == "unknown" for value in (group, limit, remaining, used)):
        #     return None
        return X_ratelimit(group=group, limit=limit, remaining=remaining, used=used)


@dataclass(slots=True)
class RequestGroupMetrics:
    """Performance metrics for a RequestGroup."""

    group_execution_started: float | None = None
    group_execution_completed: float | None = None
    group_handlers_started: float | None = None
    group_handlers_completed: float | None = None

    @property
    def group_handlers_duration(self) -> float:
        """Calculate the total duration of the group handlers."""
        if (
            self.group_handlers_started is not None
            and self.group_handlers_completed is not None
        ):
            return self.group_handlers_completed - self.group_handlers_started
        return -1.0

    @property
    def group_execution_duration(self) -> float:
        """Calculate the total duration of the group execution."""
        if (
            self.group_execution_started is not None
            and self.group_execution_completed is not None
        ):
            return self.group_execution_completed - self.group_execution_started
        return -1.0


@dataclass(slots=True)
class RequestMetrics:
    """Performance metrics for a Request."""

    task_started: float | None = None
    task_completed: float | None = None
    primary_request_started: float | None = None
    primary_request_completed: float | None = None
    paged_requests_start: float | None = None
    paged_requests_completed: float | None = None
    paged_request_count: int = 0
    handlers_started: float | None = None
    handlers_completed: float | None = None
    cache_response_status: "CachedResponseStatus | None" = None
    cache_action: "CacheAction | None" = None
    cache_check_started: float | None = None
    cache_check_completed: float | None = None
    cache_add_started: float | None = None
    cache_add_completed: float | None = None
    cache_update_started: float | None = None
    cache_update_completed: float | None = None

    @property
    def cache_add_duration(self) -> float:
        """Calculate the duration of adding a response to the cache."""
        if self.cache_add_started is not None and self.cache_add_completed is not None:
            return self.cache_add_completed - self.cache_add_started
        return -1.0

    @property
    def cache_update_duration(self) -> float:
        """Calculate the duration of updating a response in the cache."""
        if (
            self.cache_update_started is not None
            and self.cache_update_completed is not None
        ):
            return self.cache_update_completed - self.cache_update_started
        return -1.0

    @property
    def task_duration(self) -> float:
        """Calculate the total duration of the task."""
        if self.task_started is not None and self.task_completed is not None:
            return self.task_completed - self.task_started
        return -1.0

    @property
    def primary_request_duration(self) -> float:
        """Calculate the duration of the primary request."""
        if (
            self.primary_request_started is not None
            and self.primary_request_completed is not None
        ):
            return self.primary_request_completed - self.primary_request_started
        return -1.0

    @property
    def paged_requests_duration(self) -> float:
        """Calculate the total duration of the paged requests."""
        if (
            self.paged_requests_start is not None
            and self.paged_requests_completed is not None
        ):
            return self.paged_requests_completed - self.paged_requests_start
        return -1.0

    @property
    def cache_check_duration(self) -> float:
        """Calculate the duration of the cache check."""
        if (
            self.cache_check_started is not None
            and self.cache_check_completed is not None
        ):
            return self.cache_check_completed - self.cache_check_started
        return -1.0

    @property
    def handlers_duration(self) -> float:
        """Calculate the total duration of the response handlers."""
        if self.handlers_started is not None and self.handlers_completed is not None:
            return self.handlers_completed - self.handlers_started
        return -1.0


class Response(BaseModel):
    """Represents the response to an ESI request."""

    request: Request
    runtime_info: RuntimeRequestInfo
    http_response: HttpResponse | None = None
    exception_messages: list[str] = Field(default_factory=list)
    exceptions: list[Exception] = Field(..., exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ResponseGroup(BaseModel):
    """Represents the responses to a group of ESI requests."""

    request_group: RequestGroup
    runtime_info: RuntimeGroupInfo
    responses: dict[UUID, Response]


class CachedResponse(BaseModel):
    """Represents a cached response for a Request."""

    cache_key: UUID
    cached_at: Instant = Field(default_factory=_get_current_instant)
    """The instant when the response was cached."""
    http_response: HttpResponse
    expires_at: Instant | None = None
    """The instant when the cached response expires and should be considered stale."""


@dataclass(slots=True)
class IndexedOperation:
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    path: str
    operation: dict[str, Any] = field(default_factory=dict[str, Any])
    """The raw operation object from the OpenAPI schema, dereferenced and ready for use.
    
    This object contains all the details of the operation as defined in the OpenAPI schema,
    including parameters, request body, responses, and security requirements.

    <paths>:<path>:<method>:<operation> from the OpenAPI schema.

    """

    @property
    def operation_id(self) -> str:
        """Extract the operation ID from the operation object."""
        return self.operation.get("operationId", "")

    @property
    def tags(self) -> list[str]:
        """Extract the tags from the operation object, if present."""
        return self.operation.get("tags", [])

    @property
    def description(self) -> str:
        """Extract the description from the operation object, if present."""
        return self.operation.get("description", "")

    @property
    def path_params(self) -> list[dict[str, Any]]:
        """Extract the path parameters from the operation object, if present."""
        return [
            param
            for param in self.operation.get("parameters", [])
            if param.get("in") == "path"
        ]

    @property
    def query_params(self) -> list[dict[str, Any]]:
        """Extract the query parameters from the operation object, if present."""
        return [
            param
            for param in self.operation.get("parameters", [])
            if param.get("in") == "query"
        ]

    @property
    def header_params(self) -> list[dict[str, Any]]:
        """Extract the header parameters from the operation object, if present."""
        return [
            param
            for param in self.operation.get("parameters", [])
            if param.get("in") == "header"
        ]

    @property
    def request_body(self) -> dict[str, Any] | None:
        """Extract the request body from the operation object, if present."""
        return self.operation.get("requestBody")

    @property
    def auth_required(self) -> bool:
        """Determine if the operation requires authentication based on the presence of security requirements."""
        return "security" in self.operation and bool(self.operation["security"])

    @property
    def is_paged(self) -> bool:
        """Determine if the operation is paged based on the presence of pagination-related parameters."""
        for param in self.query_params:
            if param.get("name") in {"page"}:
                return True
        return False

    @property
    def is_cached(self) -> bool:
        """Determine if the operation is cacheable."""
        if self.method in {"GET", "get"}:
            return True
        return False


class IndexedEsiSchema(BaseModel):
    """Represents the entire schema for ESI requests and responses, indexed for efficient access."""

    download_date: Instant
    """The date the schema was downloaded."""
    esi_schema: dict[str, Any]
    """The raw OpenAPI schema as a dictionary."""
    operations: dict[str, IndexedOperation] = Field(default_factory=dict)
    """A mapping of operation IDs to IndexedOperation instances."""
    security_schemes: dict[str, Any] = Field(default_factory=dict)
    """A mapping of security scheme names to their definitions."""
    info: dict[str, Any] = Field(default_factory=dict)
    """The info section of the OpenAPI schema."""
    openapi: str
    """The OpenAPI version."""
    servers: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    """The servers section of the OpenAPI schema."""
    tags: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    """The tags section of the OpenAPI schema."""

    def __str__(self) -> str:
        """String representation of the IndexedEsiSchema instance."""
        return (
            f"IndexedEsiSchema(version={self.version}, "
            f"openapi={self.openapi}, operations={len(self.operations)}, "
            f"download_date={self.download_date})"
        )

    @property
    def compatibility_date(self) -> str:
        """Get the compatibility date of the ESI schema from the info section."""
        return self.version

    @property
    def version(self) -> str:
        """Get the version of the ESI schema based on the compatibility date."""
        version = cast(str, self.info["version"])
        return version

    @property
    def base_url(self) -> str:
        """Get the base URL for the ESI API from the servers section of the schema."""
        if self.servers:
            return self.servers[0]["url"]
        raise ValueError("No servers defined in schema")


class IndexedSchemaStore(BaseModel):
    """Represents a store for multiple versions of the IndexedEsiSchema.

    The compatibility date index is a string in ISO 8601 format 2026-02-21 representing
    the date that the schema version was downloaded. This allows for storing multiple
    versions of the schema and retrieving the appropriate one based on the date of the ESI
    request being executed.
    """

    schemas: dict[str, IndexedEsiSchema] = Field(default_factory=dict)
    """A mapping of download dates (as ISO 8601 strings) to IndexedEsiSchema instances."""

    def purge_older(self, cutoff_date: str) -> None:
        """Purge schemas that were downloaded before the given cutoff date.

        Args:
            cutoff_date: The ISO 8601 string representing the cutoff date. Schemas downloaded
                before this date will be removed from the store.
        """
        keys_to_purge = [key for key in self.schemas if key < cutoff_date]
        for key in keys_to_purge:
            del self.schemas[key]

    def latest_schema(self) -> IndexedEsiSchema | None:
        """Get the latest schema in the store based on download date.

        Returns:
            The IndexedEsiSchema instance with the most recent download date, or None if the store is empty.
        """
        if not self.schemas:
            return None
        latest_key = max(self.schemas.keys())
        return self.schemas[latest_key]


@dataclass(slots=True)
class GeneratedUrlInfo:
    """Represents the generated URL information for an ESI request."""

    path_url: str
    cache_url: str
    cache_key: UUID


# ---------------------------------------------------------------------------------------
# Protocols for ESI Link components. These define the expected interfaces for the various
# components of ESI Link, such as request executors, response handlers, and validators.
# ---------------------------------------------------------------------------------------


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


class RequestGroupValidatorProtocol(Protocol):
    def __call__(self, request_group: RequestGroup) -> None:
        """Validate a RequestGroup.

        Raises:
            RequestValidationError
        """
        ...


class RequestGroupExecutorProtocol(Protocol):
    _request_executor: HttpRequestExecutorProtocol
    _runtime_request_info: RuntimeRequestInfoGeneratorProtocol
    _runtime_group_info: RuntimeGroupInfoGeneratorProtocol
    _request_validator: RequestValidatorProtocol
    _request_group_validator: RequestGroupValidatorProtocol

    async def __call__(self, request_group: RequestGroup) -> ResponseGroup:
        """Execute a RequestGroup and return a ResponseGroup.

        This function should handle the entire lifecycle of executing a RequestGroup,
        including generating RuntimeRequests from the Requests in the group, validating
        the Requests, executing the RuntimeRequests, and handling the Responses to produce
        the final ResponseGroup.
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
