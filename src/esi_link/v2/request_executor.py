import asyncio
from copy import deepcopy
from typing import Any
from uuid import UUID

import aiohttp
from aiolimiter import AsyncLimiter
from whenever import Instant

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
        self.cache_manager = cache_manager
        self.max_rate = max_rate
        self.period = period
        self.force_quit = False

    async def execute_request(
        self,
        request: EsiRequest,
        session: aiohttp.ClientSession,
        rate_limiter: AsyncLimiter,
    ) -> tuple[EsiRequest, EsiResponse]:
        """Execute an ESI request and return the response.

        Exceptions will be trapped and included in the EsiResponse, but will not be raised by this method.

        Args:
            request: The EsiRequest instance to execute.
            session: An aiohttp ClientSession to use for making the HTTP request.
            rate_limiter: An AsyncLimiter instance to use for rate limiting the request.

        Returns:
            A tuple containing the original EsiRequest and an EsiResponse instance.

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
                        response = await self._get(request, session)
                    case "POST":
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
                    request_id=request.request_id,
                    response_data=None,
                    metrics=None,
                    exceptions=[e],
                )
            else:
                response.exceptions.append(e)
        return request, response

    async def execute_requests(
        self, requests: EsiRequests
    ) -> tuple[EsiRequests, dict[UUID, EsiResponse]]:
        """Execute a batch of ESI requests and return the responses.

        Args:
            requests: The EsiRequests instance containing the batch of requests to execute.

        Returns:
            A tuple containing the original EsiRequests instance and a dictionary mapping request UUIDs to EsiResponse instances.

        """
        rate_limiter = AsyncLimiter(self.max_rate, self.period)
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.execute_request(request, session, rate_limiter)
                for request in requests.requests.values()
            ]
            results = await asyncio.gather(*tasks)
            responses = {request.request_id: response for request, response in results}
            return requests, responses

    async def _get(
        self, request: EsiRequest, session: aiohttp.ClientSession
    ) -> EsiResponse:
        """Execute a GET request and return the response."""
        metrics = Metrics()
        if request.runtime_info is None:
            raise ValueError("Request runtime info is missing")
        cache_key = request.runtime_info.cache_key
        cached_response: CachedResponse | None = None
        cached_response_status: CachedResponseStatus | None = None
        if cache_key is not None:
            cached_response = self.cache_manager.get_cached_response(cache_key)
            cached_response_status = self.cache_manager.status(
                cache_key, cached_response
            )
            match cached_response_status:
                case CachedResponseStatus.VALID:
                    assert cached_response is not None
                    http_response = deepcopy(cached_response.response_data)
                    return EsiResponse(
                        request_id=request.request_id,
                        response_data=http_response,
                        metrics=metrics,
                        exceptions=[],
                    )
                case CachedResponseStatus.INVALID:
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
                request_id=request.request_id,
                response_data=http_response,
                metrics=metrics,
                exceptions=[],
            )
            # Handle response status codes
            match response.status:
                case 200:
                    if cache_key is not None:
                        self.cache_manager.set_cached_response(cache_key, http_response)
                case 304:
                    assert cache_key is not None
                    self.cache_manager.refresh_cached_response(cache_key, http_response)
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
    etag = cached_response.response_data.etag
    last_modified = cached_response.response_data.last_modified
    if etag is not None:
        request.runtime_info.headers["If-None-Match"] = etag
    if last_modified is not None:
        request.runtime_info.headers["If-Modified-Since"] = last_modified
