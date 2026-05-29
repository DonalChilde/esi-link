from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import RootModel
from whenever import Instant

from esi_link.rewrite.cache.models import CacheAction, CachedResponseStatus
from esi_link.rewrite.execution.models import HttpResponse
from esi_link.rewrite.validation.models import FailedRequestValidation, ValidatedRequest
from esi_link.type_defs import Lang


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeResponseAction:
    """Represents an action to be taken after receiving a response for a request."""

    action_type: str
    action_parameters: dict[str, Any] = field(default_factory=dict[str, Any])


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


@dataclass(slots=True, kw_only=True)
class PagedResponseMetrics:
    """Performance metrics for a paged response."""

    paged_requests_start: int | None = None
    paged_requests_completed: int | None = None
    additional_pages_count: int = 0


@dataclass(slots=True, kw_only=True)
class CachedResponseMetrics:
    """Performance metrics for a cached response."""

    cache_check_started: int | None = None
    cache_check_completed: int | None = None
    cache_action_started: int | None = None
    cache_action_completed: int | None = None


# TODO eval naming for runtime request/response


@dataclass(slots=True, kw_only=True)
class RequestMetrics:
    """Performance metrics for a Request."""

    task_started: int | None = None
    task_completed: int | None = None
    primary_request_started: int | None = None
    primary_request_completed: int | None = None
    paged_responses_metrics: PagedResponseMetrics | None = None
    cache_status: CachedResponseStatus | None = None
    cache_action: CacheAction | None = None
    cached_response_metrics: CachedResponseMetrics | None = None

    @property
    def cache_action_duration(self) -> float:
        """Calculate the duration of adding a response to the cache."""
        if self.cached_response_metrics is None:
            return -1.0
        metrics = self.cached_response_metrics
        if (
            metrics.cache_action_started is not None
            and metrics.cache_action_completed is not None
        ):
            return (
                Instant.from_timestamp_nanos(metrics.cache_action_completed)
                - Instant.from_timestamp_nanos(metrics.cache_action_started)
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
        if self.paged_responses_metrics is None:
            return -1.0
        metrics = self.paged_responses_metrics
        if (
            metrics.paged_requests_start is not None
            and metrics.paged_requests_completed is not None
        ):
            return (
                Instant.from_timestamp_nanos(metrics.paged_requests_completed)
                - Instant.from_timestamp_nanos(metrics.paged_requests_start)
            ).total("seconds")
        return -1.0

    @property
    def cache_check_duration(self) -> float:
        """Calculate the duration of the cache check."""
        if self.cached_response_metrics is None:
            return -1.0
        metrics = self.cached_response_metrics
        if (
            metrics.cache_check_started is not None
            and metrics.cache_check_completed is not None
        ):
            return (
                Instant.from_timestamp_nanos(metrics.cache_check_completed)
                - Instant.from_timestamp_nanos(metrics.cache_check_started)
            ).total("seconds")
        return -1.0


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeRequest:
    validated_request: ValidatedRequest
    """The validated request that was transformed to create this RuntimeRequest."""

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
    _actions_after_response: list[RuntimeResponseAction] = field(
        default_factory=list[RuntimeResponseAction]
    )

    @property
    def actions(self) -> list[RuntimeResponseAction]:
        """The actions to be taken after receiving a response for this request."""
        return self._actions_after_response

    @property
    def request_id(self) -> UUID:
        """The unique identifier for the request. This is used to link the request to various objects during the request lifecycle."""
        return self.validated_request.original_request.request_id


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
    failure_msg: str = ""


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeResponseGroup: ...


RuntimeResponseRoot = RootModel[RuntimeResponse]
