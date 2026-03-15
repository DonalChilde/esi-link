"""Models for ESI Link."""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, Self, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from whenever import Instant

from esi_link.helpers.pydantic.save_to_disk import BaseModelToDisk
from esi_link.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.v3.protocols import ResponseHandlerProtocol


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
    """Includes UserAgent,If-None-Match,If-Modified-Since, X-Compatibility-Date, and auth if required."""
    timeout: int = 10
    cache_key: UUID | None = None
    """Cache key for the request, if applicable. This is used to identify cached responses. Paged requests only have a cache key for the first page."""
    response_handlers: list["ResponseHandlerProtocol"] = Field(..., exclude=True)
    """The list of response handler instances to run for this request, in the order they should be run."""
    metrics: "Metrics"
    parent_id: UUID | None = None
    """The request_id of the parent request if this request is a sub-request, e.g. a paged request or a retry."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Request(BaseModelToDisk):
    """Represents a single ESI request to be executed."""

    request_id: UUID = Field(default_factory=uuid4)
    operation_id: str
    path_parameters: dict[str, str | int | float] = {}
    query_parameters: dict[str, str | int | float] = {}
    # auth_parameters: AuthParameters | None = None
    json_body: Any | None = None
    response_handlers: list[ResponseHandlerConfig] = []


class RuntimeRequest(BaseModelToDisk):
    request: Request
    runtime_info: RuntimeRequestInfo


class RequestGroup(BaseModelToDisk):
    """Represents a batch of ESI requests to be executed.

    This model exists mostly for serialization puposes, with the imagined use being
    a set of requests that are loaded from disk and run repeatedly over time. For instance,
    downloading a fresh set of pricing data every day.
    """

    created_on: Instant = Field(default_factory=_get_current_instant)
    group_id: UUID
    description: str = ""
    requests: dict[UUID, Request]


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
class Metrics:
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
    cache_stale_status_code: int = 0
    cache_check_started: float | None = None
    cache_check_completed: float | None = None

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


class Response(BaseModelToDisk):
    """Represents the response to an ESI request."""

    request: Request
    runtime_info: RuntimeRequestInfo
    http_response: HttpResponse | None = None
    exception_messages: list[str] = Field(default_factory=list)
    exceptions: list[Exception] = Field(..., exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ResponseGroup(BaseModelToDisk):
    """Represents the responses to a group of ESI requests."""

    request_group: RequestGroup
    responses: dict[UUID, Response]


class CachedResponse(BaseModelToDisk):
    """Represents a cached response for a Request."""

    cache_key: UUID
    cached_at: Instant = Field(default_factory=_get_current_instant)
    """The instant when the response was cached."""
    http_response: HttpResponse
    expires_at: Instant | None = None
    """The instant when the cached response expires and should be considered stale."""


@dataclass(slots=True)
class IndexedOperation:
    operation_id: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    path: str
    operation: dict[str, Any] = field(default_factory=dict[str, Any])

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


class IndexedEsiSchema(BaseModelToDisk):
    """Represents the entire schema for ESI requests and responses, indexed for efficient access."""

    download_date: Instant
    """The date the schema was downloaded."""
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

    @classmethod
    def from_raw_schema(
        cls,
        raw_schema: dict[str, Any],
        download_date: Instant,
    ) -> Self:
        """Factory method to create an IndexedEsiSchema instance from a raw OpenAPI schema.

        Args:
            raw_schema: The raw OpenAPI schema as a dictionary.
            download_date: The date the schema was downloaded.

        Returns:
            An instance of IndexedEsiSchema.
        """
        dereferenced_schema = resolve_internal_refs(raw_schema, raw_schema)

        operations: dict[str, IndexedOperation] = {}
        paths = dereferenced_schema.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                operation_id = operation.get("operationId")
                if operation_id:
                    operations[operation_id] = IndexedOperation(
                        operation_id=operation_id,
                        method=method.upper(),
                        path=path,
                        operation=operation,
                    )
        return cls(
            download_date=download_date,
            operations=operations,
            security_schemes=dereferenced_schema.get("components", {}).get(
                "securitySchemes", {}
            ),
            info=dereferenced_schema.get("info", {}),
            openapi=dereferenced_schema.get("openapi", ""),
            servers=dereferenced_schema.get("servers", []),
            tags=dereferenced_schema.get("tags", []),
        )


class IndexedSchemaStore(BaseModelToDisk):
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
