from dataclasses import dataclass

from esi_link.models_and_protocols import (
    CacheAction,
    CachedResponseStatus,
    Response,
    ResponseGroup,
)


@dataclass(slots=True)
class ResponseSummary:
    """A summary of a Response, containing performance metrics."""

    request_id: str
    operation: str
    url: str
    task_duration: float
    cache_check_duration: float | None
    cache_response: str | None
    cache_action: str | None
    cache_action_duration: float | None
    request_duration: float | None
    handler_duration: float | None
    paged_request_duration: float | None
    pages: int
    error_messages: list[str]


def make_response_summary(response: Response) -> ResponseSummary:
    """Create a ResponseSummary from a Response."""
    return ResponseSummary(
        request_id=str(response.request.request_id),
        operation=response.request.operation_id,
        url=response.http_response.url if response.http_response is not None else "",
        task_duration=response.runtime_info.metrics.task_duration,
        cache_check_duration=response.runtime_info.metrics.cache_check_duration,
        cache_response=str(response.runtime_info.metrics.cache_response_status),
        cache_action=str(response.runtime_info.metrics.cache_action),
        cache_action_duration=response.runtime_info.metrics.cache_action_duration,
        request_duration=response.runtime_info.metrics.primary_request_duration,
        handler_duration=response.runtime_info.metrics.handlers_duration,
        paged_request_duration=response.runtime_info.metrics.paged_requests_duration,
        pages=response.runtime_info.metrics.paged_request_count,
        error_messages=list(
            *response.network_exception_messages, *response.handler_exception_messages
        ),
    )


@dataclass
class ResponseGroupSummary:
    """A summary of a ResponseGroup, containing performance metrics."""

    request_group_id: str
    group_duration_seconds: float
    num_responses: int
    responses_with_errors: int
    responses_hit_cache: int
    """Number of responses that had cache HIT or cache STALE."""
    responses_cache_action_used: int
    """Number of responses that used the cache HIT"""
    responses_cache_action_new: int
    """Number of responses that were added to the cache."""
    responses_cache_action_update_304: int
    """Number of responses that were updated in the cache with a 304."""
    response_summaries: dict[str, ResponseSummary]


def make_response_group_summary(response_group: ResponseGroup) -> ResponseGroupSummary:
    """Create a ResponseGroupSummary from a ResponseGroup."""
    response_summaries = {
        str(response.request.request_id): make_response_summary(response)
        for response in response_group.responses.values()
    }
    return ResponseGroupSummary(
        request_group_id=str(response_group.request_group.group_id),
        group_duration_seconds=response_group.runtime_info.metrics.group_execution_duration,
        num_responses=len(response_summaries),
        responses_with_errors=sum(
            1 for summary in response_summaries.values() if summary.error_messages
        ),
        responses_hit_cache=sum(
            1
            for summary in response_summaries.values()
            if summary.cache_response
            in (CachedResponseStatus.HIT, CachedResponseStatus.STALE)
        ),
        responses_cache_action_used=sum(
            1
            for summary in response_summaries.values()
            if summary.cache_action == CacheAction.CACHED_RESPONSE_USED
        ),
        responses_cache_action_new=sum(
            1
            for summary in response_summaries.values()
            if summary.cache_action == CacheAction.ADDED_TO_CACHE
        ),
        responses_cache_action_update_304=sum(
            1
            for summary in response_summaries.values()
            if summary.cache_action == CacheAction.CACHE_304_REFRESH
        ),
        response_summaries=response_summaries,
    )
