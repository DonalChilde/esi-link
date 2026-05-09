"""Models for ESI Link."""

import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from types import TracebackType
from typing import Any, Literal, Protocol, Self, cast
from uuid import UUID, uuid4

import aiohttp
from whenever import Instant

from esi_link.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.type_defs import Lang

logger = logging.getLogger(__name__)


def _get_current_instant() -> Instant:
    """Factory function to get current instant for default values.

    This function is used as a default_factory to avoid Pydantic issue with using a
    non-callable default for a non-serializable type.

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


# @dataclass(slots=True, kw_only=True)
# class RuntimeRequestInfo:
#     """Represents the runtime information needed for a Request."""

#     path_url: str
#     additional_query_params: dict[str, str] = field(default_factory=dict[str, str])
#     """Additional query parameters that are not defined in the request, but are needed
#     for the request. Including things like the page number for paged requests."""
#     method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
#     is_paged: bool = False
#     is_auth: bool = False
#     headers: dict[str, str] = field(default_factory=dict[str, str])
#     """Includes UserAgent, If-None-Match, If-Modified-Since, X-Compatibility-Date, and auth if required."""
#     timeout: int = 10
#     cache_key: UUID | None = None
#     """Cache key for the request, if applicable. This is used to identify cached responses. Paged requests only have a cache key for the first page."""
#     metrics: "RequestMetrics"
#     parent_id: UUID | None = None
#     """The request_id of the parent request if this request is a sub-request, e.g. a paged request or a retry."""


# @dataclass(slots=True, kw_only=True)
# class RuntimeGroupInfo:
#     """Represents the runtime information for a group of ESI requests."""

#     metrics: "RequestGroupMetrics"


@dataclass(slots=True, kw_only=True, frozen=True)
class Request:
    """Represents a single ESI request to be executed.

    Can be loaded from a file or created programmatically. The request_id is used to
    identify the request.

    Requests are expected to be contained in a RequestGroup, and the request_id is used
    to link the Request to its RuntimeRequest, and to the final Response.
    """

    request_id: UUID = field(default_factory=uuid4)
    operation_id: str
    compatibility_date: str | None = None
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    authorization_id: int | None = None
    """The Character ID to use for authentication, if applicable."""
    lang: Lang = "en"
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH requests."""
    save_directory: str | None = None
    """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    save_filename: str | None = None
    """The filename to save the response data to, if applicable. If not provided, but a save_directory is provided, a default filename will be used ."""


@dataclass(slots=True, kw_only=True)
class RuntimeRequest:
    """Represents the runtime information needed for a Request."""

    request: Request
    path_url: str
    additional_query_params: dict[str, str] = field(default_factory=dict[str, str])
    """Additional query parameters that are not defined in the request, but are needed 
    for the request. Including things like the page number for paged requests."""
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    is_paged: bool = False
    is_auth: bool = False
    headers: dict[str, str] = field(default_factory=dict[str, str])
    """Includes UserAgent, If-None-Match, If-Modified-Since, X-Compatibility-Date, and auth if required."""
    timeout: int = 10
    cache_key: UUID | None = None
    """Cache key for the request, if applicable. This is used to identify cached responses. Paged requests only have a cache key for the first page."""
    metrics: "RequestMetrics" = field(default_factory=RequestMetrics)  # type: ignore
    parent_id: UUID | None = None
    """The request_id of the parent request if this request is a sub-request, e.g. a paged request or a retry."""
    error_messages: list[str] = field(default_factory=list[str])
    """A list of error messages encountered during the processing of this request, e.g. validation errors, errors from the URL generator, etc."""
    _exceptions: list[Exception] = field(
        default_factory=list[Exception], repr=False, init=False
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class RequestGroup:
    """Represents a batch of ESI requests to be executed.

    Can be loaded from a file or created programmatically. The group_id is used to
    identify the group, and can be used for things like saving response data to disk with
    a filename that includes the group_id.
    """

    created_on: Instant = field(default_factory=_get_current_instant)
    group_id: UUID
    description: str = ""
    requests: dict[UUID, Request]
    save_directory: str | None = None
    """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    save_filename: str | None = None
    """The filename to save the response group data to, if applicable. If not provided, but a save_directory is provided, a default filename will be used."""


@dataclass(slots=True, kw_only=True)
class RuntimeRequestGroup:
    """Represents the runtime information for a group of ESI requests."""

    request_group: RequestGroup
    runtime_requests: dict[UUID, RuntimeRequest]
    metrics: "RequestGroupMetrics" = field(default_factory=RequestGroupMetrics)  # type: ignore
    error_messages: list[str] = field(default_factory=list[str])
    """A list of error messages encountered during the processing of this request group, e.g. validation errors, etc."""
    _exceptions: list[Exception] = field(
        default_factory=list[Exception], repr=False, init=False
    )


@dataclass(slots=True, kw_only=True)
class X_ratelimit:
    group: str
    limit: str
    remaining: str
    used: str


@dataclass(slots=True, kw_only=True)
class HttpResponse:
    """Represents the data of an ESI response."""

    status_code: int
    url: str
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body_text: str
    received_at: int = -1
    """The timestamp when the response was received, as a Unix timestamp in nanoseconds."""
    _headers_lower: dict[str, str] = field(init=False, repr=False)

    def __post_init__(self):
        """Create a lower case version of the headers for easier access to common headers like ETag and Last-Modified."""
        self._headers_lower = {k.lower(): v for k, v in self.headers.items()}
        if len(self.headers) != len(self._headers_lower):
            logger.warning(
                "Duplicate headers found when converting to lower case. This may lead to unexpected behavior when accessing headers. Original headers: %s, Lower case headers: %s",
                self.headers,
                self._headers_lower,
            )

    @property
    def received_at_instant(self) -> Instant | None:
        """Convert the received_at timestamp to an Instant, if possible."""
        if self.received_at != -1:
            return Instant.from_timestamp_nanos(self.received_at)
        return None

    @property
    def etag(self) -> str | None:
        """Extract the ETag from the response headers, if present."""
        return self._headers_lower.get("etag")

    @property
    def last_modified(self) -> str | None:
        """Extract the Last-Modified header from the response headers, if present."""
        return self._headers_lower.get("last-modified")

    @property
    def expires(self) -> str | None:
        """Extract the Expires header from the response headers, if present."""
        return self._headers_lower.get("expires")

    @property
    def date(self) -> str | None:
        """Extract the Date header from the response headers, if present."""
        return self._headers_lower.get("date")

    @property
    def date_as_instant(self) -> Instant | None:
        """Convert the Date header to an Instant, if possible."""
        date_str = self.date
        if date_str:
            try:
                return Instant.parse_rfc2822(date_str)
            except ValueError:
                pass
        return None

    @property
    def cache_control(self) -> str | None:
        """Extract the Cache-Control header from the response headers, if present."""
        return self._headers_lower.get("cache-control")

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
        if self.max_age is not None and self.date is not None:
            try:
                response_date = Instant.parse_rfc2822(self.date)
                return response_date.add(seconds=self.max_age)
            except ValueError:
                pass
        if self.expires:
            try:
                return Instant.parse_rfc2822(self.expires)
            except ValueError:
                pass
        return None

    @property
    def pages(self) -> int:
        """Extract the number of pages from the X-Pages header, if present."""
        pages = self.headers.get("X-Pages") or self.headers.get("x-pages", 1)
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


@dataclass(slots=True, kw_only=True)
class RequestGroupMetrics:
    """Performance metrics for a RequestGroup."""

    group_execution_started: Instant | None = None
    group_execution_completed: Instant | None = None

    @property
    def group_execution_duration(self) -> float:
        """Calculate the total duration of the group execution."""
        if (
            self.group_execution_started is not None
            and self.group_execution_completed is not None
        ):
            return (
                self.group_execution_completed - self.group_execution_started
            ).total("seconds")
        return -1.0


@dataclass(slots=True)
class RequestMetrics:
    """Performance metrics for a Request."""

    task_started: Instant | None = None
    task_completed: Instant | None = None
    primary_request_started: float | None = None
    primary_request_completed: float | None = None
    paged_requests_start: float | None = None
    paged_requests_completed: float | None = None
    paged_request_count: int = 0
    cache_response_status: "CachedResponseStatus | None" = None
    cache_action: "CacheAction | None" = None
    cache_check_started: float | None = None
    cache_check_completed: float | None = None
    cache_action_started: float | None = None
    cache_action_completed: float | None = None

    @property
    def cache_action_duration(self) -> float:
        """Calculate the duration of adding a response to the cache."""
        if (
            self.cache_action_started is not None
            and self.cache_action_completed is not None
        ):
            return self.cache_action_completed - self.cache_action_started
        return -1.0

    @property
    def task_duration(self) -> float:
        """Calculate the total duration of the task."""
        if self.task_started is not None and self.task_completed is not None:
            duration = self.task_completed - self.task_started
            return duration.total("seconds")
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


@dataclass(slots=True, kw_only=True)
class Response:
    """Represents the response to an ESI request."""

    request_id: UUID
    http_response: HttpResponse | None = None
    error_messages: list[str] = field(default_factory=list[str])
    _exceptions: list[Exception] = field(
        default_factory=list[Exception], repr=False, init=False
    )


@dataclass(slots=True, kw_only=True)
class ResponseGroup:
    """Represents the responses to a group of ESI requests."""

    request_group_id: UUID
    responses: dict[UUID, Response]
    _exceptions: list[Exception] = field(
        default_factory=list[Exception], repr=False, init=False
    )


@dataclass(slots=True, kw_only=True)
class ResponseData:
    """Represents the data of a response, includes the request and response_date.

    This model is used both as a serialization format for response data, and as a
    way to pass response data to functions in a structured way.


    """

    request: Request
    response_date: str
    """Date header from the response, as an RFC 2822 string."""
    received_at: int
    """The timestamp when the response was received, as a Unix timestamp in nanoseconds."""
    data: Any
    """The actual data of the response, typically the parsed JSON body."""


@dataclass(slots=True, kw_only=True)
class CachedResponse:
    """Represents a cached response for a Request."""

    cache_key: UUID
    cached_at: Instant = field(default_factory=_get_current_instant)
    """The instant when the response was cached."""
    http_response: HttpResponse
    expires_at: Instant | None = None
    """The instant when the cached response expires and should be considered stale."""


@dataclass(slots=True)
class SchemaOperation:
    """Represents an operation defined in the ESI OpenAPI schema.

    This class is used to store the details of an operation, including the path, method,
    operation ID, and the full operation schema. This allows for easy access to the
    details of each operation when generating documentation or validating requests.

    equivalent to the combination of the path, method, and operation object from the OpenAPI schema.
    "paths":<path>:<method>:<operation_schema> from the OpenAPI schema.
    """

    path: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    operation_schema: dict[str, Any]

    @property
    def operation_id(self) -> str:
        """Extract the operation ID from the operation object."""
        return self.operation_schema.get("operationId", "")

    @property
    def tags(self) -> list[str]:
        """Extract the tags from the operation object, if present."""
        return [tag for tag in self.operation_schema.get("tags", [])]

    @property
    def description(self) -> str:
        """Extract the description from the operation object, if present."""
        return self.operation_schema.get("description", "")

    @property
    def path_and_query_parameters(self) -> list[dict[str, Any]]:
        """Extract all parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") in {"path", "query"}
        ]

    @property
    def path_params(self) -> list[dict[str, Any]]:
        """Extract the path parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "path"
        ]

    @property
    def query_params(self) -> list[dict[str, Any]]:
        """Extract the query parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "query"
        ]

    @property
    def header_params(self) -> list[dict[str, Any]]:
        """Extract the header parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "header"
        ]

    @property
    def responses(self) -> dict[str, Any]:
        """Extract the response schema from the operation object, if present."""
        success_responses = (
            self.operation_schema.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        return deepcopy(success_responses)

    @property
    def request_body(self) -> dict[str, Any] | None:
        """Extract the request body from the operation object, if present."""
        return deepcopy(self.operation_schema.get("requestBody"))

    @property
    def auth_required(self) -> bool:
        """Determine if the operation requires authentication based on the presence of security requirements."""
        return "security" in self.operation_schema and bool(
            self.operation_schema["security"]
        )

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

    @property
    def summary(self) -> str | None:
        """Extract the summary from the operation object, if present."""
        return self.operation_schema.get("summary")

    @property
    def x_values(self) -> list[dict[str, Any]]:
        """Extract the x-values from the operation object, if present."""
        x_list: list[dict[str, Any]] = []
        for key, value in self.operation_schema.items():
            if key.startswith("x-"):
                x_list.append({key: deepcopy(value)})
        return x_list


@dataclass(slots=True)
class EsiSchema:
    """Represents the ESI OpenAPI schema and its associated metadata.

    For ease of access to the details of the schema.
    """

    dereferenced_schema: dict[str, Any]

    def __post_init__(self) -> None:
        """Ensure that the schema is valid."""
        if "openapi" not in self.dereferenced_schema:
            raise ValueError("Invalid schema: missing 'openapi' field")

    @classmethod
    def from_raw_schema(cls, raw_schema: dict[str, Any]) -> Self:
        """Factory method to create an EsiSchema instance from a raw OpenAPI schema.

        This method will resolve all internal JSON references in the schema, so that
        the resulting EsiSchema instance contains a fully dereferenced schema for easy
        access to all the details of the operations defined in the schema.

        Args:
            raw_schema: The raw OpenAPI schema as a dictionary.

        Returns:
            An instance of EsiSchema with the dereferenced schema.
        """
        dereferenced_schema = resolve_internal_refs(raw_schema, raw_schema)
        return cls(dereferenced_schema=dereferenced_schema)

    @property
    def operation_ids(self) -> set[str]:
        """Extract the set of operation IDs from the schema."""
        operation_ids: set[str] = set()
        paths = self.dereferenced_schema.get("paths", {})
        for _path, methods in paths.items():
            for _method, operation in methods.items():
                operation_id = operation.get("operationId")
                if operation_id:
                    operation_ids.add(operation_id)
        return operation_ids

    @property
    def operations(self) -> dict[str, SchemaOperation]:
        """Extract the operations from the schema and return them as a dictionary mapping operation IDs to SchemaOperation instances."""
        operations: dict[str, SchemaOperation] = {}
        operation_ids = self.operation_ids
        for operation_id in operation_ids:
            operation = self.get_operation_by_id(operation_id)
            if operation:
                operations[operation_id] = operation
        return operations

    def get_operation_by_id(self, operation_id: str) -> SchemaOperation | None:
        """Get a SchemaOperation by its operation ID."""
        paths = self.dereferenced_schema.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if operation.get("operationId") == operation_id:
                    return SchemaOperation(
                        path=path,
                        method=method.upper(),
                        operation_schema=deepcopy(operation),
                    )
        return None

    @property
    def operation_id_by_tag(self) -> dict[str, list[str]]:
        """Extract a mapping of tags to operation IDs from the schema."""
        tag_mapping: dict[str, list[str]] = {}
        paths = self.dereferenced_schema.get("paths", {})
        for _path, methods in paths.items():
            for _method, operation in methods.items():
                operation_id = operation.get("operationId")
                tags = operation.get("tags", [])
                if not tags:
                    tags = ["untagged"]
                for tag in tags:
                    if tag not in tag_mapping:
                        tag_mapping[tag] = []
                    if operation_id:
                        tag_mapping[tag].append(operation_id)
        # sort the tags alphabetically, and the operation IDs within each tag alphabetically as well
        tag_mapping = {
            tag: sorted(operation_ids)
            for tag, operation_ids in sorted(tag_mapping.items())
        }
        return tag_mapping

    @property
    def compatibility_date(self) -> str:
        """Get the compatibility date of the ESI schema from the info section."""
        return self.version

    @property
    def version(self) -> str:
        """Get the version of the ESI schema based on the compatibility date."""
        version = cast(str, self.dereferenced_schema["info"]["version"])
        return version

    @property
    def base_url(self) -> str:
        """Get the base URL for the ESI API from the servers section of the schema."""
        return self.dereferenced_schema["servers"][0]["url"]


@dataclass(slots=True, kw_only=True)
class StoredSchema:
    """Represents a stored ESI schema, including the raw schema and the date it was downloaded."""

    esi_schema: EsiSchema
    download_date: Instant


@dataclass(slots=True)
class AvailableSchema:
    """Represents an available ESI schema in the SchemaManager.

    Available schemas are returned as a list of AvailableSchema, where each instance contains:
        - compatibility_date (str): The compatibility date of the schema.
        - timestamp (int): The timestamp of the schema download.
        - datetime (str): The download date and time of the schema as an ISO 8601 string.
    """

    compatibility_date: str
    timestamp: int
    datetime: str


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


# class RuntimeRequestInfoGeneratorProtocol(Protocol):
#     async def __call__(self, request: Request) -> RuntimeRequestInfo: ...


# class RuntimeGroupInfoGeneratorProtocol(Protocol):
#     def __call__(self, request_group: RequestGroup) -> RuntimeGroupInfo: ...


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
    # _runtime_request_info: RuntimeRequestInfoGeneratorProtocol
    # _runtime_group_info: RuntimeGroupInfoGeneratorProtocol
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


class CacheManagerProtocol:
    # TODO Returned CachedResponses should not have any connection to the cache data.
    # This would happen naturally with some cache implemetations, like a per file cache
    # where each CachedResponse is read from a separate file, but for in-memory caches
    # we need to make sure that the CachedResponse instances returned by get, set, and
    # refresh are copies of the data stored in the cache, to avoid unintended side effects
    # from modifying the returned CachedResponse directly. This should be called out in
    # the docstrings for these methods, and we should make sure to implement this behavior
    # in any in-memory cache implementations.

    # TODO change the prtocol to async, to allow for async cache implementations, e.g.,
    # a cache that uses an async database client.

    # TODO batch writes to the cache, and provide a hot cache for recently accessed items. See Claude's suggestions for cache management strategies.
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
    def generate_path_url(self, request: Request, schema: EsiSchema) -> str:
        """Generate the url path for an ESI request based on its parameters.\

        This url does not contain query parameters, and is not suitable for generateing
        a cache key. It is used as the url argument for http requests, assuming that
        query parameters are sent separately.
        """
        ...

    def generate_cache_url(self, request: Request, schema: EsiSchema) -> str:
        """Generate the url to use for cache key generation for an ESI request based on its parameters.

        This url should contain all path and most query parameters, and should be
        consistent for requests that should share a cache key. It is used for generating
        cache keys, and is not necessarily the same as the url used for making the http request.

        NOTE: Validate the request before generating the cache url, to ensure that all
        required parameters are present and correctly formatted, to avoid generating
        different cache urls for requests that should share a cache key.
        """
        ...

    def generate_cache_key(self, request: Request, schema: EsiSchema) -> UUID:
        """Generate a cache key for an ESI request based on its parameters.

        The key is usually generated by hashing the url generated by generate_cache_url,
        but can be any UUID that is consistently generated for requests that should share
        a cache key.
        """
        ...

    def __call__(self, request: Request, schema: EsiSchema) -> GeneratedUrlInfo:
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
    ) -> StoredSchema:
        """Get the ESI schema corresponding to the given compatibility date and timestamp.

        Args:
            compatibility_date (str): The compatibility date of the schema to retrieve.
            timestamp (int): The timestamp of the schema to retrieve.

        Returns:
            StoredSchema: The ESI schema corresponding to the given compatibility date and timestamp.

        Raises:
            SchemaNotFoundError: If no schema is found for the given compatibility date and timestamp.
            SchemaManagerError: If there is an error loading the schema file.
        """
        ...

    def get_latest_schema(self, compatibility_date: str | None) -> StoredSchema:
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
