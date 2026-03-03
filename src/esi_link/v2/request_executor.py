"""Module for executing ESI requests, including handling HTTP requests, caching, and rate limiting."""

import asyncio
import logging
from collections.abc import Iterable
from copy import deepcopy
from time import perf_counter
from typing import Any

import aiohttp
from aiolimiter import AsyncLimiter

from esi_link.v2.models import (
    CachedResponse,
    CachedResponseStatus,
    CacheManagerProtocol,
    EsiRequestExecutorProtocol,
    EsiResponse,
    EsiRuntimeRequest,
    HttpResponse,
    Metrics,
)

logger = logging.getLogger(__name__)


class EsiRequestExecutor(EsiRequestExecutorProtocol):
    def __init__(
        self, cache_manager: CacheManagerProtocol, max_rate: int, period: float
    ):
        """Executor for ESI requests that handles making HTTP requests, caching, and rate limiting."""
        self.cache_manager = cache_manager
        self.max_rate = max_rate
        self.period = period
        self.force_quit = False
        self.async_limiter = AsyncLimiter(max_rate, period)

    async def execute_request(
        self,
        request: EsiRuntimeRequest,
        session: aiohttp.ClientSession,
    ) -> EsiResponse:
        """Execute an ESI request and return the response.

        Exceptions will be trapped and included in the EsiResponse, but will not be raised by this method.

        Args:
            request: The EsiRuntimeRequest instance to execute.
            session: An aiohttp ClientSession to use for making the HTTP request.

        Returns:
            An EsiResponse instance corresponding to the executed request.

        """
        response: EsiResponse | None = None
        metrics = Metrics()
        metrics.task_started = perf_counter()
        try:
            async with self.async_limiter:
                if self.force_quit:
                    raise RuntimeError("Request execution was forcefully stopped")
                match request.runtime_info.method:
                    case "GET":
                        metrics.primary_request_started = perf_counter()
                        response = await self._get(request, session, metrics)
                        metrics.primary_request_completed = perf_counter()
                        if self.is_paged_response_required(response):
                            await self.complete_paged_response(
                                response, session, metrics
                            )
                    case "POST":
                        metrics.primary_request_started = perf_counter()
                        response = await self._post(request, session, metrics)
                        metrics.primary_request_completed = perf_counter()
                        if await self.is_paged_response_required(response):
                            await self.complete_paged_response(
                                response, session, metrics
                            )
                    case "PUT":
                        metrics.primary_request_started = perf_counter()
                        response = await self._put(request, session, metrics)
                        metrics.primary_request_completed = perf_counter()
                        if await self.is_paged_response_required(response):
                            await self.complete_paged_response(
                                response, session, metrics
                            )
                    case "DELETE":
                        metrics.primary_request_started = perf_counter()
                        response = await self._delete(request, session, metrics)
                        metrics.primary_request_completed = perf_counter()
                        if await self.is_paged_response_required(response):
                            await self.complete_paged_response(
                                response, session, metrics
                            )
                    case _:
                        raise ValueError(
                            f"Unsupported HTTP method: {request.runtime_info.method}"
                        )
        except Exception as e:
            metrics.task_completed = perf_counter()
            if response is None:
                response = EsiResponse(
                    request=request.request,
                    runtime_info=request.runtime_info,
                    http_response=None,
                    metrics=metrics,
                    exception_messages=[str(e)],
                    exceptions=[e],
                )
            else:
                response.exception_messages.append(str(e))
                response.exceptions.append(e)
        metrics.task_completed = perf_counter()
        return response

    async def execute_requests(
        self, requests: Iterable[EsiRuntimeRequest]
    ) -> list[EsiResponse]:
        """Execute a batch of ESI requests and return the responses.

        Args:
            requests: An iterable of EsiRuntimeRequest instances to execute.

        Returns:
            A list of EsiResponse instances corresponding to the executed requests.

        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.execute_request(request, session) for request in requests]
            results = await asyncio.gather(*tasks)
            return results

    def is_paged_response_required(self, response: EsiResponse) -> bool:
        """Determine if a paged request requires additional requests to retrieve all pages of data.

        If the current page is page 1, and there are more than one page of data (as
        indicated by the presence of the X-Pages header), then additional requests are
        required to retrieve all pages of data.

        if the current page is greater than one, then we are already in the process of
        retrieving paged data, and no additional requests are required.
        """
        if response.http_response is None:
            return False
        # page defaults to 1 if not present, so we can assume it's always an int
        current_page = int(response.runtime_info.additional_query_params.get("page", 1))
        x_page_count = response.http_response.pages
        if x_page_count > 1 and current_page == 1:
            return True
        return False

    def _check_for_valid_paged_reponses(
        self, response: EsiResponse, paged_responses: list[EsiResponse]
    ) -> None:
        """Check if the paged responses are valid.

        Rasies an exception if any of the paged responses are invalid, such as having a
        different Last-Modified header than the original response, or having a non-200
        status code.
        """
        check_for_valid_paged_reponses(response, paged_responses)

    def _combine_paged_response_strings(
        self, response: EsiResponse, paged_responses: list[EsiResponse]
    ) -> str:
        """Combine the body text from the original response and the paged responses into a single string."""
        try:
            paged_strings = collect_paged_response_strings(paged_responses)
            combined_string = combine_paged_response_strings(
                response.http_response.body_text if response.http_response else "",
                paged_strings,
            )
        except Exception as e:
            raise ValueError(
                f"Failed to combine paged response strings for request {response.request.request_id}: {str(e)}"
            ) from e
        return combined_string

    async def complete_paged_response(
        self, first_page: EsiResponse, session: aiohttp.ClientSession, metrics: Metrics
    ) -> EsiResponse:
        """Complete a paged request by making additional HTTP requests to retrieve all pages of data.

        When the requests are complete, combine the paged data into the first response and return it.
        """
        if first_page.http_response is None:
            raise ValueError(
                "Cannot complete paged response for a response with no HTTP response"
            )
        if first_page.metrics is None:
            raise ValueError(
                "Metrics should be initialized in the response before completing paged requests"
            )
        paged_requests = self._assemble_paged_runtime_requests(first_page)
        first_page.metrics.paged_requests_start = perf_counter()
        paged_responses = await asyncio.gather(
            *[self.execute_request(request, session) for request in paged_requests]
        )
        first_page.metrics.paged_requests_completed = perf_counter()
        self._check_for_valid_paged_reponses(first_page, paged_responses)
        combined_response_string = self._combine_paged_response_strings(
            first_page, paged_responses
        )
        first_page.http_response.body_text = combined_response_string
        return first_page

    def _assemble_paged_runtime_requests(
        self, response: EsiResponse
    ) -> list[EsiRuntimeRequest]:
        """Assemble the additional EsiRuntimeRequest instances required to complete a paged request."""
        try:
            return assemble_paged_runtime_requests(response)
        except Exception as e:
            raise ValueError(
                f"Failed to assemble paged requests for response to request {response.request.request_id}: {str(e)}"
            ) from e

    async def _get(
        self,
        request: EsiRuntimeRequest,
        session: aiohttp.ClientSession,
        metrics: Metrics,
    ) -> EsiResponse:
        """Execute a GET request and return the response."""
        cache_key = request.runtime_info.cache_key
        cached_response: CachedResponse | None = None
        if cache_key is not None:
            metrics.cache_check_started = perf_counter()
            cached_response, status = self.cache_manager.get(cache_key)
            metrics.cache_check_completed = perf_counter()
            match status:
                case CachedResponseStatus.HIT:
                    assert cached_response is not None
                    metrics.cache_response_status = CachedResponseStatus.HIT
                    http_response = deepcopy(cached_response.http_response)
                    return EsiResponse(
                        request=request.request,
                        runtime_info=request.runtime_info,
                        http_response=http_response,
                        metrics=metrics,
                        exceptions=[],
                    )
                case CachedResponseStatus.MISS:
                    # update from esi
                    metrics.cache_response_status = CachedResponseStatus.MISS
                case CachedResponseStatus.STALE:
                    assert cached_response is not None
                    metrics.cache_response_status = CachedResponseStatus.STALE
                    set_stale_cache_headers(request, cached_response)
        query_parameters: dict[str, Any] = (
            request.request.query_parameters
            | request.runtime_info.additional_query_params
        )

        async with session.get(
            request.runtime_info.path_url,
            params=query_parameters,
            headers=request.runtime_info.headers,
        ) as response:
            response_text = await response.text()
            http_response = HttpResponse(
                status_code=response.status,
                url=str(response.url),
                headers=dict(response.headers),
                body_text=response_text,
            )
            esi_response = EsiResponse(
                request=request.request,
                runtime_info=request.runtime_info,
                http_response=http_response,
                metrics=metrics,
                exceptions=[],
            )
            # Handle response status codes
            match response.status:
                case 200:
                    if self.is_paged_response_required(esi_response):
                        # Don't cache the response yet, since we need to get the paged responses first
                        response = await self.complete_paged_response(
                            esi_response, session, metrics
                        )
                    if cache_key is not None:
                        if metrics.cache_response_status == CachedResponseStatus.STALE:
                            metrics.cache_stale_status_code = 200
                        self.cache_manager.set(cache_key, http_response)
                case 304:
                    if cache_key is None:
                        raise ValueError(
                            "Received 304 Not Modified response for a request with no cache key"
                        )
                    metrics.cache_stale_status_code = 304
                    cached_response = self.cache_manager.refresh(
                        cache_key, http_response
                    )
                    esi_response.http_response = deepcopy(cached_response.http_response)
                case _:
                    logger.error(
                        f"Received unexpected status code {response.status} for request {request.request.request_id}"
                    )
                    response.raise_for_status()
            return esi_response

    async def _post(
        self,
        request: EsiRuntimeRequest,
        session: aiohttp.ClientSession,
        metrics: Metrics,
    ) -> EsiResponse:
        """Execute a POST request and return the response."""
        ...

    async def _put(
        self,
        request: EsiRuntimeRequest,
        session: aiohttp.ClientSession,
        metrics: Metrics,
    ) -> EsiResponse:
        """Execute a PUT request and return the response."""
        ...

    async def _delete(
        self,
        request: EsiRuntimeRequest,
        session: aiohttp.ClientSession,
        metrics: Metrics,
    ) -> EsiResponse:
        """Execute a DELETE request and return the response."""
        ...


def set_stale_cache_headers(
    request: EsiRuntimeRequest, cached_response: CachedResponse
) -> None:
    """Set the appropriate cache headers on the request based on the cached response."""
    etag = cached_response.http_response.etag
    last_modified = cached_response.http_response.last_modified
    if etag is not None:
        request.runtime_info.headers["If-None-Match"] = etag
    if last_modified is not None:
        request.runtime_info.headers["If-Modified-Since"] = last_modified


# TODO merge paged data
# TODO validate last-modified for paged data.


def assemble_paged_runtime_requests(response: EsiResponse) -> list[EsiRuntimeRequest]:
    """Assemble the additional EsiRuntimeRequest instances required to complete a paged request."""
    if response.http_response is None:
        raise ValueError(
            "Cannot assemble paged requests for a response with no HTTP response"
        )
    total_pages = response.http_response.pages
    if response.metrics is not None:
        response.metrics.paged_request_count = total_pages
    paged_runtime_requests: list[EsiRuntimeRequest] = []
    for page in range(2, total_pages + 1):
        new_request = EsiRuntimeRequest(
            request=deepcopy(response.request),
            runtime_info=deepcopy(response.runtime_info),
        )
        new_request.runtime_info.additional_query_params["page"] = str(page)
        paged_runtime_requests.append(new_request)
    return paged_runtime_requests


def check_for_valid_paged_reponses(
    response: EsiResponse, paged_responses: list[EsiResponse]
) -> None:
    """Check that the paged responses are valid and can be combined with the original response."""
    if response.http_response is None:
        raise ValueError(
            "Cannot check paged responses for a response with no HTTP response"
        )
    for paged_response in paged_responses:
        page_num = paged_response.runtime_info.additional_query_params.get(
            "page", "unknown"
        )
        if paged_response.http_response is None:
            raise ValueError(
                f"Invalid paged response: page {page_num} has no HTTP response"
            )
        if paged_response.http_response.status_code != 200:
            raise ValueError(
                f"Invalid paged response: page {page_num} has an unexpected status code {paged_response.http_response.status_code}"
            )
        if (
            paged_response.http_response.last_modified
            != response.http_response.last_modified
        ):
            raise ValueError(
                f"Invalid paged response: page {page_num} has a different Last-Modified header than the original response"
            )


def collect_paged_response_strings(paged_responses: list[EsiResponse]) -> list[str]:
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
