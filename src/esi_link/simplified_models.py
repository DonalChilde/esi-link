import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self, cast
from uuid import UUID, uuid4

from pydantic import RootModel
from whenever import Instant

from esi_link.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.type_defs import Lang

logger = logging.getLogger(__name__)


# TODO
# - flesh out models
# flow is: Request -> ValidatedRequest -> RuntimeRequest -> RuntimeResponse -> Response
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


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeResponseAction:
    """Represents an action to be taken after receiving a response for a request."""

    action_type: str
    action_parameters: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseGroupAction:
    """Represents an action to be taken after receiving a group of responses."""

    action_type: str
    action_parameters: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(slots=True, kw_only=True, frozen=True)
class Request:
    """Represents a single ESI request to be executed.

    Can be loaded from a file or created programmatically. The request_id is used to
    identify the request.

    Requests can be be contained in a RequestGroup, and the request_id is used
    to link the Request to its RuntimeRequest, and to the final Response.
    """

    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various objects during the request lifecycle."""
    created_on: Instant = field(default_factory=_get_current_instant)
    """The timestamp of when the request was created. This is used for things like determining the age of the request, or for saving response data to disk with a filename that includes the creation date."""
    operation_id: str
    """The operation ID of the request, corresponding to the operationId in the ESI OpenAPI schema."""
    compatibility_date: str | None = None
    """Optional compatibility date for the request. If not provided, the latest schema will be used."""
    at_or_after: int | None = None
    """Used with compatibility date. Optional timestamp to refine compatibility date selection. If provided, the schema with the compatibility date that was downloaded after the provided timestamp will be used."""
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The path parameters for the request, if applicable. This is used to fill in the path parameters in the URL template."""
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The query parameters for the request, if applicable. This is used to fill in the query parameters in the URL template."""
    authorization_id: int | None = None
    """The Character ID to use for authentication, if applicable."""
    language: Lang = "en"
    """The language to use for the request, if applicable. This is used to set the Accept-Language header in the request."""
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH requests."""
    actions_after_response: list[RuntimeResponseAction] = field(
        default_factory=list[RuntimeResponseAction]
    )
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""


@dataclass(slots=True, kw_only=True, frozen=True)
class ValidatedRequest:
    """Represents a validated ESI request, ready to be executed.

    The path, query, and json body parameters are duplicated from the original Request,
    but are now validated and ready to be used for the actual HTTP request to ESI. This
    allows for manipulation of the parameters during validation without affecting the
    original Request object, which can be useful for ensuring that the params used match
    the program's expectations. e.g. page is a valid query parameter for a paged operation,
    but the program may want to set it to 1 if it's not provided in the original Request,
    and this way the original Request remains unchanged, while the ValidatedRequest has
    the page parameter set to 1 for use in the actual HTTP request to ESI.

    Additional fields are added to capture required info from the schema for the request,
    such as the path URL template, HTTP method, and whether the request is paged or cacheable.
    This allows for easy access to this information during the execution of the request,
    without needing to refer back to the original Request or the ESI schema.

    """

    # These fields are copied from the original Request, but are now validated and ready
    # to be used for the actual HTTP request to ESI.

    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various objects during the request lifecycle."""
    created_on: Instant = field(default_factory=_get_current_instant)
    """The timestamp of when the request was created. This is used for things like determining the age of the request, or for saving response data to disk with a filename that includes the creation date."""
    operation_id: str = "NOT_SET"
    """The operation ID of the request, corresponding to the operationId in the ESI OpenAPI schema."""
    compatibility_date: str | None = None
    """Optional compatibility date for the request. If not provided, the latest schema will be used."""
    at_or_after: int | None = None
    """Used with compatibility date. Optional timestamp to refine compatibility date selection. If provided, the schema with the compatibility date that was downloaded after the provided timestamp will be used."""
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The path parameters for the request, if applicable. This is used to fill in the path parameters in the URL template."""
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The query parameters for the request, if applicable. This is used to fill in the query parameters in the URL template."""
    authorization_id: int | None = None
    """The Character ID to use for authentication, if applicable."""
    language: Lang = "en"
    """The language to use for the request, if applicable. This is used to set the Accept-Language header in the request."""
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH requests."""
    actions_after_response: list[RuntimeResponseAction] = field(
        default_factory=list[RuntimeResponseAction]
    )
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""

    # These fields are added to capture required info from the schema for the request,
    # such as the path URL template, HTTP method, and whether the request is paged or cacheable.
    path_url_template: str = ""
    """The URL template for the path."""
    method: Literal[
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "NOT_SET"
    ] = "NOT_SET"
    """The HTTP method for the request."""
    is_paged: bool = False
    """Whether the request is paged or not, based on the presence of pagination-related parameters in the operation schema."""
    is_cached: bool = False
    """Whether the request is cacheable or not, based on the HTTP method of the operation."""
    is_authentication_required: bool = False
    """Whether the request requires authentication or not, based on the presence of security requirements in the operation schema."""


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedRequestValidation:
    request: Request
    """The original request that failed validation."""
    errors: tuple[str, ...]
    """A list of error messages describing the validation failures."""


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
    response_actions: list[ResponseGroupAction] = field(
        default_factory=list[ResponseGroupAction]
    )
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response group data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""


@dataclass(slots=True, kw_only=True, frozen=True)
class ValidatedRequestGroup:
    """Represents a validated batch of ESI requests, ready to be executed."""

    # These fields are copied from the original RequestGroup, but are now validated and
    # ready to be executed. The requests field is now a dictionary of ValidatedRequest,
    # and an additional field is added to capture any failed request validations, which
    # is a dictionary of FailedRequestValidation.
    created_on: Instant
    group_id: UUID
    description: str
    requests: dict[UUID, ValidatedRequest] = field(
        default_factory=dict[UUID, ValidatedRequest]
    )
    response_actions: list[ResponseGroupAction] = field(
        default_factory=list[ResponseGroupAction]
    )
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response group data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""

    failed_request_validations: dict[UUID, FailedRequestValidation] = field(
        default_factory=dict[UUID, FailedRequestValidation]
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedRequestGroupValidation:
    request_group: RequestGroup
    """The original request group that failed validation."""
    errors: tuple[str, ...]
    """A list of error messages describing the validation failures."""


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

    task_started: int | None = None
    task_completed: int | None = None
    primary_request_started: int | None = None
    primary_request_completed: int | None = None
    paged_requests_start: int | None = None
    paged_requests_completed: int | None = None
    additional_pages_count: int = 0
    cache_response_status: CachedResponseStatus | None = None
    cache_action: CacheAction | None = None
    cache_check_started: int | None = None
    cache_check_completed: int | None = None
    cache_action_started: int | None = None
    cache_action_completed: int | None = None

    @property
    def cache_action_duration(self) -> float:
        """Calculate the duration of adding a response to the cache."""
        if (
            self.cache_action_started is not None
            and self.cache_action_completed is not None
        ):
            return (
                Instant.from_timestamp_nanos(self.cache_action_completed)
                - Instant.from_timestamp_nanos(self.cache_action_started)
            ).total("seconds")
        return -1.0

    @property
    def task_duration(self) -> float:
        """Calculate the total duration of the task."""
        if self.task_started is not None and self.task_completed is not None:
            return (
                Instant.from_timestamp_nanos(self.task_completed)
                - Instant.from_timestamp_nanos(self.task_started)
            ).total("seconds")
        return -1.0

    @property
    def primary_request_duration(self) -> float:
        """Calculate the duration of the primary request."""
        if (
            self.primary_request_started is not None
            and self.primary_request_completed is not None
        ):
            return (
                Instant.from_timestamp_nanos(self.primary_request_completed)
                - Instant.from_timestamp_nanos(self.primary_request_started)
            ).total("seconds")
        return -1.0

    @property
    def paged_requests_duration(self) -> float:
        """Calculate the total duration of the paged requests."""
        if (
            self.paged_requests_start is not None
            and self.paged_requests_completed is not None
        ):
            return (
                Instant.from_timestamp_nanos(self.paged_requests_completed)
                - Instant.from_timestamp_nanos(self.paged_requests_start)
            ).total("seconds")
        return -1.0

    @property
    def cache_check_duration(self) -> float:
        """Calculate the duration of the cache check."""
        if (
            self.cache_check_started is not None
            and self.cache_check_completed is not None
        ):
            return (
                Instant.from_timestamp_nanos(self.cache_check_completed)
                - Instant.from_timestamp_nanos(self.cache_check_started)
            ).total("seconds")
        return -1.0


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeRequest:
    # These fields are copied from the original ValidatedRequestGroup, but are now ready
    # to be executed.
    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various objects during the request lifecycle."""
    created_on: Instant = field(default_factory=_get_current_instant)
    """The timestamp of when the request was created. This is used for things like determining the age of the request, or for saving response data to disk with a filename that includes the creation date."""
    operation_id: str = "NOT_SET"
    """The operation ID of the request, corresponding to the operationId in the ESI OpenAPI schema."""
    compatibility_date: str | None = None
    """Optional compatibility date for the request. If not provided, the latest schema will be used."""
    at_or_after: int | None = None
    """Used with compatibility date. Optional timestamp to refine compatibility date selection. If provided, the schema with the compatibility date that was downloaded after the provided timestamp will be used."""
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The path parameters for the request, if applicable. This is used to fill in the path parameters in the URL template."""
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The query parameters for the request, if applicable. This is used to fill in the query parameters in the URL template."""
    authorization_id: int | None = None
    """The Character ID to use for authentication, if applicable."""
    language: Lang = "en"
    """The language to use for the request, if applicable. This is used to set the Accept-Language header in the request."""
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH requests."""
    actions_after_response: list[RuntimeResponseAction] = field(
        default_factory=list[RuntimeResponseAction]
    )
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""
    path_url_template: str = ""
    """The URL template for the path."""
    method: Literal[
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "NOT_SET"
    ] = "NOT_SET"
    """The HTTP method for the request."""
    is_paged: bool = False
    """Whether the request is paged or not, based on the presence of pagination-related 
    parameters in the operation schema."""
    is_cached: bool = False
    """Whether the request is cacheable or not, based on the HTTP method of the operation."""
    is_authentication_required: bool = False
    """Whether the request requires authentication or not, based on the presence of security 
    requirements in the operation schema."""

    # These fields are determined prior to executing the request.
    path_url: str = ""
    """The resolved URL for the request, after filling in the path parameters in the URL template."""
    cache_url: str = ""
    """The URL used for caching the request, which is the path url plus most query parameters. 
    This is used to generate the cache UUID for a  request. For paged requests, the 
    cache_url does not include the page query parameter, so that all pages of a paged 
    request can be identified as the same request for caching purposes."""
    additional_query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """Additional query parameters that are not defined in the request, but are needed 
    for the request. Including things like the page number for paged requests."""
    headers: dict[str, str] = field(default_factory=dict[str, str])
    """Includes UserAgent, If-None-Match, If-Modified-Since, X-Compatibility-Date, and 
    Bearer token if required."""
    timeout: int = 10
    """The timeout for the request, in seconds."""
    cache_key: UUID | None = None
    """Cache key for the request, if applicable. This is used to identify cached responses. 
    Paged requests only have a cache key for the first page."""
    metrics: RequestMetrics = field(default_factory=RequestMetrics)
    parent_id: UUID | None = None
    """The request_id of the parent request if this request is a sub-request, e.g. a paged 
    request or a retry."""

    # # These fields are determined after the request is executed
    # save_directory: Path | None = None
    # """The directory to save the response data to, if applicable. This is the resolved directory after filling in any templates. If not provided, response data will not be saved to disk."""
    # save_filename: str | None = None
    # """The filename to save the response data to, if applicable. This is the resolved filename after filling in any templates. If not provided, but a save_directory is provided, a default filename will be used."""


@dataclass(slots=True, kw_only=True)
class RuntimeRequestGroup:
    # These fields are copied from the original ValidatedRequestGroup, but are now ready
    # to be executed. The requests field is now a dictionary of RuntimeRequest.
    created_on: Instant
    group_id: UUID
    description: str
    requests: dict[UUID, RuntimeRequest] = field(
        default_factory=dict[UUID, RuntimeRequest]
    )
    actions_after_response: list[RuntimeResponseAction] = field(
        default_factory=list[RuntimeResponseAction]
    )
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response group data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""

    failed_request_validations: dict[UUID, FailedRequestValidation] = field(
        default_factory=dict[UUID, FailedRequestValidation]
    )
    # These fields are determined prior to executing the requests in the group.
    metrics: RequestGroupMetrics = field(default_factory=RequestGroupMetrics)
    # These fields are determined after the requests are executed
    save_directory: Path | None = None
    """The directory to save the response data to, if applicable. This is the resolved directory after filling in any templates. If not provided, response data will not be saved to disk."""
    save_filename: str | None = None
    """The filename to save the response data to, if applicable. This is the resolved filename after filling in any templates. If not provided, but a save_directory is provided, a default filename will be used."""


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeResponse:
    http_response: HttpResponse
    runtime_request: RuntimeRequest


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedRuntimeResponse:
    runtime_request: RuntimeRequest
    http_response: HttpResponse | None
    failure_reason: str


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeResponseGroup: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class Response:
    http_response: HttpResponse
    runtime_request: RuntimeRequest


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseGroup:
    group_id: UUID
    description: str = ""
    responses: dict[UUID, Response] = field(default_factory=dict[UUID, Response])
    metrics: RequestGroupMetrics = field(default_factory=RequestGroupMetrics)
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response group data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""


@dataclass(slots=True, kw_only=True, frozen=True)
class X_ratelimit:
    group: str
    limit: str
    remaining: str
    used: str


@dataclass(slots=True, kw_only=True, frozen=True)
class HttpResponse:
    """Represents the data of an ESI response."""

    status_code: int
    url: str
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body_text: str
    received_at: int = -1
    """The timestamp when the response was received, as a Unix timestamp in nanoseconds."""
    _headers_lower: dict[str, str] = field(
        init=False, repr=False, default_factory=dict[str, str]
    )

    def __post_init__(self):
        """Create a lower case version of the headers for easier access to common headers like ETag and Last-Modified."""
        self._headers_lower.update({k.lower(): v for k, v in self.headers.items()})
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
    def body_as_json(self) -> Any | None:
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


@dataclass(slots=True, kw_only=True, frozen=True)
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
    def path_parameters(self) -> list[dict[str, Any]]:
        """Extract the path parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "path"
        ]

    @property
    def query_parameters(self) -> list[dict[str, Any]]:
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
    def is_authentication_required(self) -> bool:
        """Determine if the operation requires authentication based on the presence of security requirements."""
        return "security" in self.operation_schema and bool(
            self.operation_schema["security"]
        )

    @property
    def is_paged(self) -> bool:
        """Determine if the operation is paged based on the presence of pagination-related parameters."""
        for param in self.query_parameters:
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


@dataclass(slots=True, kw_only=True, frozen=True)
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

    @property
    def content_languages(self) -> set[str]:
        """Get the content languages supported by the ESI API from the schema."""
        return set(
            self.dereferenced_schema.get("components", {})
            .get("headers", {})
            .get("ContentLanguage", {})
            .get("schema", {})
            .get("enum", [])
        )


@dataclass(slots=True, kw_only=True, frozen=True)
class StoredSchema:
    """Represents a stored ESI schema, including the raw schema and the date it was downloaded."""

    esi_schema: EsiSchema
    download_date: Instant


@dataclass(slots=True, kw_only=True, frozen=True)
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


@dataclass(slots=True, kw_only=True, frozen=True)
class CachedResponse:
    """Represents a cached response for a Request."""

    cache_key: UUID
    cached_at: Instant = field(default_factory=_get_current_instant)
    """The instant when the response was cached."""
    http_response: HttpResponse
    expires_at: Instant | None = None
    """The instant when the cached response expires and should be considered stale."""

    @property
    def is_expired(self) -> bool:
        """Determine if the cached response is expired based on the current time and the expires_at instant."""
        if self.expires_at is None:
            return False
        return Instant.now() >= self.expires_at

    @property
    def cache_age(self) -> float:
        """Calculate the age of the cached response in seconds."""
        return (Instant.now() - self.cached_at).total("seconds")


RuntimeResponseRoot = RootModel[RuntimeResponse]
