"""Module for executing ESI requests, including handling HTTP requests, caching, and rate limiting."""

import asyncio
from copy import deepcopy

import aiohttp
from aiolimiter import AsyncLimiter

from esi_link.v2.models import (
    CachedResponse,
    CachedResponseStatus,
    CacheManagerProtocol,
    EsiRequest,
    EsiRequestExecutorProtocol,
    EsiRequests,
    EsiResponse,
    HttpResponse,
    Metrics,
)


class EsiRequestExecutor(EsiRequestExecutorProtocol):
    def __init__(
        self, cache_manager: CacheManagerProtocol, max_rate: int, period: float
    ):
        """Executor for ESI requests that handles making HTTP requests, caching, and rate limiting."""
        self.cache_manager = cache_manager
        self.max_rate = max_rate
        self.period = period
        self.force_quit = False

    async def execute_request(
        self,
        request: EsiRequest,
        session: aiohttp.ClientSession,
        rate_limiter: AsyncLimiter,
    ) -> EsiResponse:
        """Execute an ESI request and return the response.

        Exceptions will be trapped and included in the EsiResponse, but will not be raised by this method.

        Args:
            request: The EsiRequest instance to execute.
            session: An aiohttp ClientSession to use for making the HTTP request.
            rate_limiter: An AsyncLimiter instance to use for rate limiting the request.

        Returns:
            An EsiResponse instance corresponding to the executed request.

        """
        response: EsiResponse | None = None
        try:
            if request.runtime_info is None:
                raise ValueError("Request runtime info is missing")
            async with rate_limiter:
                if self.force_quit:
                    raise RuntimeError("Request execution was forcefully stopped")
                match request.runtime_info.method:
                    case "GET":
                        if request.runtime_info.is_paged:
                            pass  # TODO: implement pagination handling
                        response = await self._get(request, session)
                    case "POST":
                        if request.runtime_info.is_paged:
                            pass  # TODO: implement pagination handling
                        response = await self._post(request, session)
                    case "PUT":
                        response = await self._put(request, session)
                    case "DELETE":
                        response = await self._delete(request, session)
                    case _:
                        raise ValueError(
                            f"Unsupported HTTP method: {request.runtime_info.method}"
                        )
        except Exception as e:
            if response is None:
                response = EsiResponse(
                    request=request,
                    http_response=None,
                    metrics=None,
                    exception_messages=[str(e)],
                    exceptions=[e],
                )
            else:
                response.exception_messages.append(str(e))
                response.exceptions.append(e)
        return response

    async def execute_requests(self, requests: EsiRequests) -> list[EsiResponse]:
        """Execute a batch of ESI requests and return the responses.

        Args:
            requests: The EsiRequests instance containing the batch of requests to execute.

        Returns:
            A list of EsiResponse instances corresponding to the executed requests.

        """
        rate_limiter = AsyncLimiter(self.max_rate, self.period)
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.execute_request(request, session, rate_limiter)
                for request in requests.requests.values()
            ]
            results = await asyncio.gather(*tasks)

            return results

    async def _get(
        self, request: EsiRequest, session: aiohttp.ClientSession
    ) -> EsiResponse:
        """Execute a GET request and return the response."""
        metrics = Metrics()
        if request.runtime_info is None:
            raise ValueError("Request runtime info is missing")
        cache_key = request.runtime_info.cache_key
        cached_response: CachedResponse | None = None
        if cache_key is not None:
            cached_response, status = self.cache_manager.get(cache_key)

            match status:
                case CachedResponseStatus.HIT:
                    assert cached_response is not None
                    http_response = deepcopy(cached_response.http_response)
                    return EsiResponse(
                        request=request,
                        http_response=http_response,
                        metrics=metrics,
                        exceptions=[],
                    )
                case CachedResponseStatus.MISS:
                    # update from esi
                    pass
                case CachedResponseStatus.STALE:
                    assert cached_response is not None
                    set_cache_headers(request, cached_response)

        async with session.get(
            request.runtime_info.url, params=request.query_parameters
        ) as response:
            response_data = await response.json()
            http_response = HttpResponse(
                status_code=response.status,
                headers=dict(response.headers),
                body=response_data,
            )
            esi_response = EsiResponse(
                request=request,
                http_response=http_response,
                metrics=metrics,
                exceptions=[],
            )
            # Handle response status codes
            match response.status:
                case 200:
                    if cache_key is not None:
                        self.cache_manager.set(cache_key, http_response)
                case 304:
                    assert cache_key is not None
                    self.cache_manager.refresh(cache_key, http_response)
                case _:
                    response.raise_for_status()
            return esi_response

    async def _post(
        self, request: EsiRequest, session: aiohttp.ClientSession
    ) -> EsiResponse:
        """Execute a POST request and return the response."""
        ...

    async def _put(
        self, request: EsiRequest, session: aiohttp.ClientSession
    ) -> EsiResponse:
        """Execute a PUT request and return the response."""
        ...

    async def _delete(
        self, request: EsiRequest, session: aiohttp.ClientSession
    ) -> EsiResponse:
        """Execute a DELETE request and return the response."""
        ...


def set_cache_headers(request: EsiRequest, cached_response: CachedResponse) -> None:
    """Set the appropriate cache headers on the request based on the cached response."""
    if request.runtime_info is None:
        raise ValueError("Request runtime info is missing")
    etag = cached_response.http_response.etag
    last_modified = cached_response.http_response.last_modified
    if etag is not None:
        request.runtime_info.headers["If-None-Match"] = etag
    if last_modified is not None:
        request.runtime_info.headers["If-Modified-Since"] = last_modified
