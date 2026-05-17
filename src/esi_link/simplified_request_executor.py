"""An implementation of the HttpRequestExecutorProtocol.

Provides caching, rate limiting, and pagination for ESI requests.
"""

import asyncio
import logging
from copy import deepcopy
from dataclasses import asdict, replace
from typing import cast

import aiohttp
from aiolimiter import AsyncLimiter
from whenever import Instant

from esi_link.simplified_models import (
    CacheAction,
    CachedResponse,
    CachedResponseStatus,
    FailedRuntimeResponse,
    HttpResponse,
    RuntimeRequest,
    RuntimeResponse,
)
from esi_link.simplified_protocols import CacheManagerProtocol

logger = logging.getLogger(__name__)


def _update_stale_cache_headers(
    request: RuntimeRequest, cached_response: CachedResponse
) -> RuntimeRequest:
    """Update the headers of the request to include information about the stale cache response."""
    if not cached_response.is_expired:
        return request
    updated_headers = deepcopy(request.headers)
    etag = cached_response.http_response.etag
    last_modified = cached_response.http_response.last_modified
    if etag:
        updated_headers["If-None-Match"] = etag
    if last_modified:
        updated_headers["If-Modified-Since"] = last_modified

    return replace(request, headers=updated_headers)


async def execute_request_with_cache(
    request: RuntimeRequest,
    session: aiohttp.ClientSession,
    rate_limiter: AsyncLimiter,
    cache_manager: CacheManagerProtocol,
) -> RuntimeResponse | FailedRuntimeResponse:
    """Execute the HTTP request with caching and rate limiting."""
    cache_key = request.cache_key
    request.metrics.cache_check_started = Instant.now().timestamp_nanos()
    if cache_key is None:
        # No cache key means this request is not cacheable, so we execute it directly without checking the cache
        logger.info(
            f"No cache key for request {request.path_url}, executing without cache"
        )
        request.metrics.cache_check_completed = Instant.now().timestamp_nanos()
        return await execute_http_request(request, session, rate_limiter)
    cached_response = await cache_manager.get(cache_key)
    request.metrics.cache_check_completed = Instant.now().timestamp_nanos()
    if cached_response is None:
        # Cache miss - no cached response found for this cache key
        request.metrics.cache_response_status = CachedResponseStatus.MISS
        logger.info(
            f"Cache miss (not found) for request {request.path_url} with cache key {cache_key}"
        )
        response = await execute_http_request(request, session, rate_limiter)
        if isinstance(response, FailedRuntimeResponse):
            logger.error(
                f"HTTP request failed, cache not updated for {request.path_url} with cache key {cache_key}: {response.failure_reason}"
            )
            return response
        request.metrics.cache_action_started = Instant.now().timestamp_nanos()
        request.metrics.cache_action = CacheAction.ADDED_TO_CACHE
        await cache_manager.set(cache_key, response.http_response)
        request.metrics.cache_action_completed = Instant.now().timestamp_nanos()
        logger.info(
            f"Cached response for request {response.http_response.url} with cache key {cache_key}, expires at {response.http_response.expires_at}"
        )
        return response
    if cached_response.is_expired:
        # Cache miss - cached response is expired
        logger.info(
            f"Cache miss (stale) for request {cached_response.http_response.url} with cache key {cache_key}"
        )
        request = _update_stale_cache_headers(request, cached_response)
        request.metrics.cache_response_status = CachedResponseStatus.STALE
        response = await execute_http_request(request, session, rate_limiter)
        if isinstance(response, FailedRuntimeResponse):
            logger.error(
                f"HTTP request failed when validating stale cache for {request.path_url} with cache key {cache_key}: {response.failure_reason}. Returning stale cached response with status code {cached_response.http_response.status_code}"
            )
            return response
        if response.http_response.status_code == 304:
            # Cached response is still valid, refresh the cache with the new response data and return the cached response
            request.metrics.cache_action_started = Instant.now().timestamp_nanos()
            request.metrics.cache_action = CacheAction.CACHE_304_REFRESH
            cached_response = await cache_manager.refresh(
                cache_key, response.http_response
            )
            request.metrics.cache_action_completed = Instant.now().timestamp_nanos()
            logger.info(
                f"Refreshed cache for request {response.http_response.url} with new response, expires at {cached_response.expires_at}"
            )
            return RuntimeResponse(
                http_response=cached_response.http_response,
                runtime_request=request,
            )
        elif response.http_response.status_code == 200:
            # We got a new valid response, so we update the cache with the new response and return it
            request.metrics.cache_action_started = Instant.now().timestamp_nanos()
            request.metrics.cache_action = CacheAction.ADDED_TO_CACHE
            cached_response = await cache_manager.set(cache_key, response.http_response)
            request.metrics.cache_action_completed = Instant.now().timestamp_nanos()
            logger.info(
                f"Updated cache for request {response.http_response.url} with new response, expires at {cached_response.expires_at}"
            )
            return response
        else:
            logger.warning(
                f"Received unexpected status code {response.http_response.status_code} for request {response.http_response.url} when validating stale cache, returning cached response with status code {cached_response.http_response.status_code}"
            )
            return response
    else:
        # Cache hit - cached response is valid
        logger.info(
            f"Cache hit for request {cached_response.http_response.url} with cache key {cache_key}"
        )
        request.metrics.cache_response_status = CachedResponseStatus.HIT
        return RuntimeResponse(
            http_response=cached_response.http_response,
            runtime_request=request,
        )


async def execute_http_request(
    request: RuntimeRequest,
    session: aiohttp.ClientSession,
    rate_limiter: AsyncLimiter,
) -> RuntimeResponse | FailedRuntimeResponse:
    """Execute the HTTP request with rate limiting."""
    request.metrics.primary_request_started = Instant.now().timestamp_nanos()
    async with rate_limiter:
        query_params = request.query_parameters | request.additional_query_parameters
        async with session.request(
            method=request.method,
            url=request.path_url,
            headers=request.headers,
            params=query_params,
            json=request.json_body,
        ) as resp:
            logger.info(
                f"Made HTTP request to {resp.real_url} with method {request.method} and received status code {resp.status}"
            )
            content = ""
            http_response = None
            try:
                content = await resp.text()
                http_response = HttpResponse(
                    status_code=resp.status,
                    url=str(resp.real_url),
                    headers=dict(resp.headers),
                    body_text=content,
                    received_at=Instant.now().timestamp_nanos(),
                )
                request.metrics.primary_request_completed = (
                    Instant.now().timestamp_nanos()
                )
                resp.raise_for_status()
            except aiohttp.ClientResponseError as e:
                logger.error(
                    f"HTTP request failed: {e} with response content: {content}"
                )
                response = FailedRuntimeResponse(
                    http_response=http_response,
                    runtime_request=request,
                    failure_reason=str(e),
                )
                return response
            response = RuntimeResponse(
                http_response=http_response,
                runtime_request=request,
            )
            request.metrics.primary_request_completed = Instant.now().timestamp_nanos()
            additional_requests = await _check_for_additional_page_requests(response)
            if not additional_requests:
                return response
            request.metrics.paged_requests_start = Instant.now().timestamp_nanos()
            request.metrics.additional_pages_count = len(additional_requests)
            additional_responses = await asyncio.gather(
                *[
                    execute_http_request(req, session, rate_limiter)
                    for req in additional_requests
                ]
            )
            request.metrics.paged_requests_completed = Instant.now().timestamp_nanos()
            for paged_response in additional_responses:
                if isinstance(paged_response, FailedRuntimeResponse):
                    logger.error(
                        f"Failed to fetch additional page for request {request.path_url}: {paged_response.failure_reason}"
                    )
                    return FailedRuntimeResponse(
                        http_response=response.http_response,
                        runtime_request=request,
                        failure_reason=f"Failed to fetch additional page: {paged_response.failure_reason}",
                    )
            # At this point, we have successfully fetched all additional pages, so we
            # can combine the responses into a single response to return to the caller
            additional_responses = cast(list[RuntimeResponse], additional_responses)
            try:
                _check_for_valid_paged_responses(response, additional_responses)
                combined_response = _combine_paged_responses(
                    response, additional_responses
                )
            except Exception as e:
                logger.error(
                    f"Invalid paged responses for request {request.path_url}: {str(e)}"
                )
                return FailedRuntimeResponse(
                    http_response=response.http_response,
                    runtime_request=request,
                    failure_reason=f"Invalid paged responses: {str(e)}",
                )

            return combined_response


async def _check_for_additional_page_requests(
    response: RuntimeResponse,
) -> list[RuntimeRequest]:
    """Check if the response indicates that there are additional pages of data to fetch."""
    if not response.runtime_request.is_paged:
        return []

    current_page = response.runtime_request.additional_query_parameters.get("page", -1)
    # If the current page is not 1, then we know this is not the first page of results,
    # so we can skip checking for additional pages and just return the response as is.
    if current_page != 1:
        return []
    total_pages = response.http_response.pages
    if total_pages <= 1:
        return []
    additional_requests: list[RuntimeRequest] = []
    for page in range(2, total_pages + 1):
        new_request = deepcopy(response.runtime_request)
        additional_query_parameters = new_request.additional_query_parameters.copy()
        additional_query_parameters["page"] = page
        new_request = replace(
            new_request, additional_query_parameters=additional_query_parameters
        )
        additional_requests.append(new_request)
    return additional_requests


def _combine_paged_responses(
    first_page: RuntimeResponse, paged_responses: list[RuntimeResponse]
) -> RuntimeResponse:
    """Combine the responses from multiple pages of data into a single response."""
    paged_strings = _collect_paged_response_strings(paged_responses)
    combined_string = _combine_paged_response_strings(
        first_page.http_response.body_text, paged_strings
    )
    updated_http_response = replace(first_page.http_response, body_text=combined_string)
    return replace(first_page, http_response=updated_http_response)


def _combine_paged_response_strings(first_page: str, paged_strings: list[str]) -> str:
    """Combine the body text from the original response and the paged responses into a single string."""
    # This logic assumes that the body of the response is a JSON array of items,
    # which is true for many ESI endpoints, but may not be universally true.
    # We may need to make this logic more robust in the future.

    if first_page.startswith("[") and first_page.endswith("]"):
        return _combine_list_of_array_strings(first_page, paged_strings)
    else:
        raise ValueError(
            "Cannot combine paged response strings: original string is not a JSON array"
        )


def _combine_list_of_array_strings(first_page: str, paged_strings: list[str]) -> str:
    """Combine the body text from the original response and the paged responses into a single json string list of items."""
    fragments: list[str] = []
    if first_page.startswith("[") and first_page.endswith("]"):
        fragments.append(first_page[1:-1])  # Remove the brackets
        for page_num, paged_string in enumerate(paged_strings, start=2):
            if paged_string.startswith("[") and paged_string.endswith("]"):
                fragments.append(paged_string[1:-1])  # Remove the brackets
            else:
                raise ValueError(
                    f"Cannot combine paged response strings: paged string is not a JSON array: page {page_num}"
                )
        combined_string = f"[{','.join(fragments)}]"  # Add the brackets back
        return combined_string
    else:
        raise ValueError(
            "Cannot combine paged response strings: original string is not a JSON array"
        )


def _collect_paged_response_strings(
    paged_responses: list[RuntimeResponse],
) -> list[str]:
    """Collect the body text from a list of paged responses."""
    response_strings: list[str] = []
    for paged_response in paged_responses:
        page_num = paged_response.runtime_request.additional_query_parameters.get(
            "page", "unknown"
        )
        if not paged_response.http_response.body_text:
            raise ValueError(
                f"Cannot collect response string from a paged response with no body text: page {page_num}"
            )
        response_strings.append(paged_response.http_response.body_text)
    return response_strings


def _check_for_valid_paged_responses(
    response: RuntimeResponse, paged_responses: list[RuntimeResponse]
) -> None:
    """Check that the paged responses are valid and can be combined with the original response.

    Raises:
        ValueError: If any of the paged responses are invalid and cannot be combined with
            the original response.
    """
    for paged_response in paged_responses:
        page_num = paged_response.runtime_request.additional_query_parameters.get(
            "page", "unknown"
        )
        if paged_response.http_response.status_code != 200:
            logger.error(
                f"Received unexpected status code {paged_response.http_response.status_code} "
                f"for paged response to request {response.runtime_request.request_id} page {page_num}"
                f"\n{asdict(paged_response.http_response)}"
            )
            raise ValueError(
                f"Invalid paged response: page {page_num} has an unexpected status code {paged_response.http_response.status_code}"
            )
        if (
            paged_response.http_response.last_modified
            != response.http_response.last_modified
        ):
            logger.error(
                f"Received paged response with different Last-Modified header for request {response.runtime_request.request_id} page {page_num}. "
                f"Original Last-Modified: {response.http_response.last_modified}, "
                f"Paged Last-Modified: {paged_response.http_response.last_modified}"
            )
            raise ValueError(
                f"Invalid paged response: page {page_num} has a different Last-Modified "
                "header than the original response. This may indicate that the data changed "
                "between requests, and the paged responses may not be valid. Try again."
            )
