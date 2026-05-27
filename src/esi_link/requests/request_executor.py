"""An implementation of the HttpRequestExecutorProtocol.

Provides caching, rate limiting, and pagination for ESI requests.
"""

import asyncio
import logging
from copy import deepcopy
from time import perf_counter
from uuid import UUID, uuid4

import aiohttp
from aiolimiter import AsyncLimiter
from whenever import Instant

from esi_link.rewrite.cache.models import (
    CacheAction,
    CachedResponse,
    CachedResponseStatus,
)
from esi_link.rewrite.execution.models import HttpResponse
from esi_link.rewrite.request.models import Response
from esi_link.rewrite.runtime.models import RuntimeRequest
from esi_link.rewrite.simplified_models import (
    CacheManagerProtocol,
    HttpRequestExecutorProtocol,
)

logger = logging.getLogger(__name__)


class RequestExecutor(HttpRequestExecutorProtocol):
    def __init__(
        self,
        cache_manager: CacheManagerProtocol,
        rate_limiter: AsyncLimiter,
    ):
        """Initialize the request executor with the given cache manager and rate limiter."""
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter

    async def __call__(
        self, request: RuntimeRequest, session: aiohttp.ClientSession
    ) -> Response:
        """Execute the given request, utilizing caching and rate limiting."""
        metrics = request.runtime_info.metrics
        metrics.task_started = Instant.now()
        cached_response, cache_status = pre_check_cache(request, self.cache_manager)
        if cached_response is not None:
            return cached_response
        try:
            metrics.primary_request_started = perf_counter()
            response = await execute_http_request(request, session, self.rate_limiter)
            metrics.primary_request_completed = perf_counter()
        except Exception as e:
            logger.error(f"Error executing HTTP request: {e}")
            return Response(
                request=request.request,
                runtime_info=request.runtime_info,
                http_response=None,
                network_exception_messages=[str(e)],
                exceptions=[e],
            )

        # Check for 304 Not Modified if we had a stale cache hit
        response = handle_304_not_modified(response, self.cache_manager, cache_status)
        response = await check_for_pages(response, session, self.rate_limiter)
        cache_id = update_cache_if_needed(response, self.cache_manager)
        _ = cache_id
        return response


async def execute_http_request(
    request: RuntimeRequest,
    session: aiohttp.ClientSession,
    rate_limiter: AsyncLimiter,
) -> Response:
    """Execute the HTTP request with rate limiting."""
    async with rate_limiter:
        query_params = (
            request.request.query_parameters
            | request.runtime_info.additional_query_params
        )

        async with session.request(
            method=request.runtime_info.method,
            url=request.runtime_info.path_url,
            headers=request.runtime_info.headers,
            params=query_params,
            json=request.request.json_body,
        ) as resp:
            logger.info(
                f"Made HTTP request to {resp.real_url} with method {request.runtime_info.method} and received status code {resp.status}"
            )
            content = ""
            try:
                content = await resp.text()
                resp.raise_for_status()
            except aiohttp.ClientResponseError as e:
                logger.exception(
                    f"HTTP request failed: {e} with response content: {content}"
                )
                raise e
            http_response = HttpResponse(
                status_code=resp.status,
                url=str(resp.real_url),
                headers=dict(resp.headers),
                body_text=content,
                received_timestamp=Instant.now().timestamp_nanos(),
            )
            return Response(
                request=request.request,
                runtime_info=request.runtime_info,
                http_response=http_response,
                network_exception_messages=[],
                exceptions=[],
            )


def update_cache_if_needed(
    response: Response,
    cache_manager: CacheManagerProtocol,
) -> UUID | None:
    """Update the cache with the new response if caching is applicable."""
    if response.http_response is None:
        raise ValueError("Cannot update cache for a response with no HTTP response")
    if response.runtime_info.cache_key is not None:
        metrics = response.runtime_info.metrics
        metrics.cache_action_started = perf_counter()
        cache_manager.set(response.runtime_info.cache_key, response.http_response)
        metrics.cache_action_completed = perf_counter()
        metrics.cache_action = CacheAction.ADDED_TO_CACHE
        return response.runtime_info.cache_key
    return None


def is_paged_response_required(response: Response) -> bool:
    """Determine if a paged request requires additional requests to retrieve all pages of data.

    If the current page is page 1, and there are more than one page of data (as
    indicated by the presence of the X-Pages header), then additional requests are
    required to retrieve all pages of data.

    if the current page is greater than one, then we are already in the process of
    retrieving paged data, and no additional requests are required.
    """
    # page defaults to 1 if not present, so we can assume it's always an int
    current_page = int(response.runtime_info.additional_query_params.get("page", 1))
    assert response.http_response is not None  # for mypy
    x_page_count = response.http_response.pages
    if x_page_count > 1 and current_page == 1:
        return True
    return False


async def check_for_pages(
    response: Response,
    session: aiohttp.ClientSession,
    rate_limiter: AsyncLimiter,
) -> Response:
    """Check if the response indicates pagination and handle it if necessary."""
    if not is_paged_response_required(response):
        return response
    metrics = response.runtime_info.metrics
    metrics.paged_request_count = response.http_response.pages  # type: ignore
    requests = assemble_paged_runtime_requests(response)
    metrics.paged_requests_start = perf_counter()
    paged_responses = await asyncio.gather(
        *[execute_http_request(req, session, rate_limiter) for req in requests]
    )
    logger.info(
        f"Completed {len(paged_responses)} paged requests for original request {response.request.request_id} to url {response.http_response.url}"
    )
    metrics.paged_requests_completed = perf_counter()

    check_for_valid_paged_responses(response, paged_responses)
    response = combine_responses(response, paged_responses)
    logger.info(
        f"Combined paged responses for original request {response.request.request_id} into a single response with url {response.http_response.url}"
    )
    return response


def combine_responses(
    first_page: Response, paged_responses: list[Response]
) -> Response:
    """Combine the body text from the original response and the paged responses into a single response.

    Mutates first_page to have the combined body text, and returns it for convenience.
    """
    if first_page.http_response is None:
        raise ValueError(
            "Cannot combine paged responses for a response with no HTTP response"
        )
    paged_strings = collect_paged_response_strings(paged_responses)
    combined_string = combine_paged_response_strings(
        first_page.http_response.body_text, paged_strings
    )
    first_page.http_response.body_text = combined_string
    return first_page


def assemble_paged_runtime_requests(response: Response) -> list[RuntimeRequest]:
    """Assemble the additional EsiRuntimeRequest instances required to complete a paged request."""
    if response.http_response is None:
        raise ValueError(
            "Cannot assemble paged requests for a response with no HTTP response"
        )
    metrics = response.runtime_info.metrics  # a convenience for shorter lines.
    total_pages = response.http_response.pages
    metrics.paged_request_count = total_pages
    paged_runtime_requests: list[RuntimeRequest] = []
    for page in range(2, total_pages + 1):
        new_request = RuntimeRequest(
            request=deepcopy(response.request),
            runtime_info=deepcopy(response.runtime_info),
        )
        new_request.runtime_info.parent_id = response.request.request_id
        new_request.request.request_id = uuid4()
        new_request.runtime_info.additional_query_params["page"] = str(page)
        new_request.runtime_info.cache_key = (
            None  # paged requests are not cached individually
        )
        paged_runtime_requests.append(new_request)
    logger.info(
        f"Assembled {len(paged_runtime_requests)} paged requests for original request {response.request.request_id} to url {response.http_response.url}"
    )
    return paged_runtime_requests


def handle_304_not_modified(
    response: Response,
    cache_manager: CacheManagerProtocol,
    cache_status: CachedResponseStatus,
) -> Response:
    """Handle a 304 Not Modified response by returning the cached response."""
    if response.http_response is None:
        raise ValueError(
            "Cannot handle 304 Not Modified for a response with no HTTP response"
        )
    if (
        response.http_response.status_code == 304
        and cache_status == CachedResponseStatus.STALE
        and response.runtime_info.cache_key is not None
    ):
        metrics = response.runtime_info.metrics
        metrics.cache_action_started = perf_counter()
        cached_response = cache_manager.refresh(
            response.runtime_info.cache_key, response.http_response
        )
        metrics.cache_action_completed = perf_counter()
        metrics.cache_action = CacheAction.CACHE_304_REFRESH
        response.http_response = cached_response.http_response
    return response


def pre_check_cache(
    request: RuntimeRequest, cache_manager: CacheManagerProtocol
) -> tuple[Response | None, CachedResponseStatus]:
    """Check the cache for a response before making an HTTP request."""
    if request.runtime_info.cache_key is None:
        # no cache_key means we can't cache this request,
        # so we can skip the cache check entirely
        return None, CachedResponseStatus.MISS
    metrics = request.runtime_info.metrics
    metrics.cache_check_started = perf_counter()
    cached_response, status = cache_manager.get(request.runtime_info.cache_key)
    metrics.cache_check_completed = perf_counter()
    if status == CachedResponseStatus.HIT and cached_response is not None:
        metrics.cache_response_status = CachedResponseStatus.HIT
        metrics.cache_action = CacheAction.CACHED_RESPONSE_USED
        metrics.cache_action_started = metrics.cache_check_started
        metrics.cache_action_completed = metrics.cache_check_completed
        logger.info(
            f"Cache hit for request {request.request.request_id} to path_url {request.runtime_info.path_url}"
        )
        return Response(
            request=request.request,
            runtime_info=request.runtime_info,
            http_response=cached_response.http_response,
            network_exception_messages=[],
            exceptions=[],
        ), status
    if status == CachedResponseStatus.STALE and cached_response is not None:
        metrics.cache_response_status = CachedResponseStatus.STALE
        logger.info(
            f"Stale cache hit for request {request.request.request_id} to path_url {request.runtime_info.path_url}"
        )
        set_stale_cache_headers(request, cached_response)
        return None, status
    if status == CachedResponseStatus.MISS and cached_response is None:
        metrics.cache_response_status = CachedResponseStatus.MISS
        logger.info(
            f"Cache miss for request {request.request.request_id} to path_url {request.runtime_info.path_url}"
        )
        return None, status
    raise ValueError(
        f"Invalid cache response and status combination: {status} with cached_response {cached_response}"
    )


def set_stale_cache_headers(
    request: RuntimeRequest, cached_response: CachedResponse
) -> None:
    """Set the appropriate cache headers on the request based on the cached response."""
    etag = cached_response.http_response.etag
    last_modified = cached_response.http_response.last_modified
    if etag is not None:
        request.runtime_info.headers["If-None-Match"] = etag
    elif last_modified is not None:
        request.runtime_info.headers["If-Modified-Since"] = last_modified
    else:
        raise ValueError(
            "Cannot set stale cache headers: cached response has no ETag or Last-Modified header"
        )


def combine_paged_response_strings(first_page: str, paged_strings: list[str]) -> str:
    """Combine the body text from the original response and the paged responses into a single string."""
    # This logic assumes that the body of the response is a JSON array of items,
    # which is true for many ESI endpoints, but may not be universally true.
    # We may need to make this logic more robust in the future.

    if first_page.startswith("[") and first_page.endswith("]"):
        return combine_list_of_array_strings(first_page, paged_strings)
    else:
        raise ValueError(
            "Cannot combine paged response strings: original string is not a JSON array"
        )


def combine_list_of_array_strings(first_page: str, paged_strings: list[str]) -> str:
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


def collect_paged_response_strings(paged_responses: list[Response]) -> list[str]:
    """Collect the body text from a list of paged responses."""
    response_strings: list[str] = []
    for paged_response in paged_responses:
        page_num = paged_response.runtime_info.additional_query_params.get(
            "page", "unknown"
        )
        if paged_response.http_response is None:
            raise ValueError(
                f"Cannot collect response string from a paged response with no HTTP response: page {page_num}"
            )
        if not paged_response.http_response.body_text:
            raise ValueError(
                f"Cannot collect response string from a paged response with no body text: page {page_num}"
            )
        response_strings.append(paged_response.http_response.body_text)
    return response_strings


def check_for_valid_paged_responses(
    response: Response, paged_responses: list[Response]
) -> None:
    """Check that the paged responses are valid and can be combined with the original response.

    Raises:
        ValueError: If any of the paged responses are invalid and cannot be combined with
            the original response.
    """
    if response.http_response is None:
        logger.error(
            f"Cannot check paged responses for a response with no HTTP response, request ID: {response.request.request_id}"
        )
        raise ValueError(
            "Cannot check paged responses for a response with no HTTP response"
        )
    for paged_response in paged_responses:
        page_num = paged_response.runtime_info.additional_query_params.get(
            "page", "unknown"
        )
        if paged_response.http_response is None:
            logger.error(
                f"Received invalid paged response with no HTTP response for request {response.request.request_id} page {page_num}"
            )
            raise ValueError(
                f"Invalid paged response: page {page_num} has no HTTP response"
            )
        if paged_response.http_response.status_code != 200:
            logger.error(
                f"Received unexpected status code {paged_response.http_response.status_code} "
                f"for paged response to request {response.request.request_id} page {page_num}"
                f"\n{paged_response.model_dump_json(indent=2)}"
            )
            raise ValueError(
                f"Invalid paged response: page {page_num} has an unexpected status code {paged_response.http_response.status_code}"
            )
        if (
            paged_response.http_response.last_modified
            != response.http_response.last_modified
        ):
            logger.error(
                f"Received paged response with different Last-Modified header for request {response.request.request_id} page {page_num}. "
                f"Original Last-Modified: {response.http_response.last_modified}, "
                f"Paged Last-Modified: {paged_response.http_response.last_modified}"
            )
            raise ValueError(
                f"Invalid paged response: page {page_num} has a different Last-Modified "
                "header than the original response. This may indicate that the data changed "
                "between requests, and the paged responses may not be valid. Try again."
            )
