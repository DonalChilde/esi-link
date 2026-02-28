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
                        if await self.is_paged_response_required(response):
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

    async def is_paged_response_required(self, response: EsiResponse) -> bool:
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
        if all(
            (
                "X-Pages" in response.http_response.headers,
                x_page_count > 1,
                current_page == 1,
            )
        ):
            return True
        return False

    async def complete_paged_response(
        self, response: EsiResponse, session: aiohttp.ClientSession, metrics: Metrics
    ) -> EsiResponse:
        """Complete a paged request by making additional HTTP requests to retrieve all pages of data.

        When the requests are complete, combine the paged data into the first response and return it.
        """
        paged_requests = self.assemble_paged_requests(response)
        assert response.metrics is not None, (
            "Metrics should be initialized in the response before completing paged requests"
        )
        response.metrics.paged_requests_start = perf_counter()
        paged_responses = await asyncio.gather(
            *[self.execute_request(request, session) for request in paged_requests]
        )
        response.metrics.paged_requests_completed = perf_counter()
        # Combine the paged data into the first response
        for paged_response in paged_responses:
            if (
                paged_response.http_response is not None
                and response.http_response is not None
                and response.http_response.body is not None  # type: ignore
            ):
                # This logic assumes that the body of the response is a list of items,
                # which is true for many ESI endpoints, but may not be universally true.
                # We may need to make this logic more robust in the future.
                if isinstance(response.http_response.body, list) and isinstance(  # type: ignore
                    paged_response.http_response.body, list
                ):
                    response.http_response.body.extend(  # type: ignore
                        paged_response.http_response.body  # type: ignore
                    )
                else:
                    raise ValueError(
                        "Cannot combine paged response data: response bodies are not lists"
                    )
            else:
                raise ValueError(
                    "Cannot combine paged response data: one of the responses has no HTTP response or body"
                )
        return response

    def assemble_paged_requests(self, response: EsiResponse) -> list[EsiRuntimeRequest]:
        """Assemble the additional EsiRuntimeRequest instances required to complete a paged request."""
        if response.http_response is None:
            raise ValueError(
                "Cannot assemble paged requests for a response with no HTTP response"
            )
        total_pages = response.http_response.pages
        assert response.metrics is not None, (
            "Metrics should be initialized in the response before assembling paged requests"
        )
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
