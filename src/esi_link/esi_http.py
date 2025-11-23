"""ESI HTTP Client Implementations."""

import asyncio
import logging
from copy import deepcopy
from types import CoroutineType, TracebackType
from typing import Any, Literal

import aiohttp
from aiolimiter import AsyncLimiter
from whenever import Instant

from esi_link.helpers import header_funcs as HF
from esi_link.helpers.build_url import build_url
from esi_link.models import (
    CacheProtocol,
    EsiHttpProtocol,
    EsiLinkError,
    EsiResponse,
    EsiSchema,
    HttpRequest,
    HttpResponse,
    Metrics,
)

logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------
# EsiHttpProtocol Implementations
# ---------------------------------------------------------------------------


class EsiHttpRateLimited(EsiHttpProtocol):
    """An ESI HTTP client implementation that collects requests and processes them asynchronously."""

    def __init__(
        self,
        cache: CacheProtocol,
        esi_schema: EsiSchema,
        max_rate: int = 100,
        time_period: float = 60.0,
    ) -> None:
        """Initialize the EsiHttpRateLimited instance."""
        self.session: aiohttp.ClientSession | None = None
        self.cache = cache
        self.esi_schema = esi_schema
        self.max_rate = max_rate
        self.time_period = time_period
        self._error_count: int = 0

    async def __aenter__(self) -> "EsiHttpRateLimited":
        """Enter the async context manager, initializing the HTTP session and rate limiter."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        self.limiter = AsyncLimiter(self.max_rate, self.time_period)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager, closing the HTTP session."""
        assert self.session is not None, "Session is not initialized."
        await self.session.close()

    async def _worker(self, request: HttpRequest) -> EsiResponse:
        """Worker to process a single HTTP request.

        Args:
            request: The HttpRequest instance to process.

        Returns:
            A tuple of the HttpRequest and either None or an exception if one occurred.
        """
        metrics = Metrics()
        metrics.request_start = Instant.now()
        cache_status: Literal["HIT", "MISS", "STALE", "NA"] | None = None
        http_response: HttpResponse | None = None
        try:
            if not self.session:
                raise EsiLinkError("HTTP session is not initialized.")
            # cache key should be None if resource is not cached.
            if request.cache_key is None:
                cache_status = "NA"
            else:
                metrics.cache_check_start = Instant.now()
                cached_response = self.cache.get_cached_response(request.cache_key)
                metrics.cache_check_end = Instant.now()
                if cached_response is None:
                    cache_status = "MISS"
                    metrics.cache_check = "MISS"
                else:
                    if cached_response.is_stale():
                        cache_status = "STALE"
                        metrics.cache_check = "STALE"
                        # Add conditional headers to the request
                        # Use ETag and Last-Modified from the cached response
                        if cached_response.response.etag:
                            request.headers["If-None-Match"] = (
                                cached_response.response.etag
                            )
                        if cached_response.response.last_modified:
                            request.headers["If-Modified-Since"] = (
                                cached_response.response.last_modified
                            )
                    else:
                        cache_status = "HIT"
                        metrics.cache_check = "HIT"
                        metrics.response_source = "CACHE"
                        metrics.request_end = Instant.now()
                        return EsiResponse(
                            request=request.esi_request,
                            http_response=cached_response.response,
                            metrics=metrics,
                        )
            http_response = await self.get_response(request, metrics=metrics)
            if metrics.response_start and metrics.response_end:
                logger.info(
                    f"Processed http request for URL {request.url} in "
                    f"{(metrics.response_end - metrics.response_start).in_seconds():.2f} seconds."
                    f"Status code {http_response.status_code}, Reason: {http_response.reason}"
                )
            # Update metrics with rate limit information from response headers
            metrics_rate_limits(metrics, http_response)
            match http_response.status_code:
                case 200:
                    if request.is_paged:
                        await self.get_paged_data(
                            request=request, first_page=http_response, metrics=metrics
                        )
                    metrics.response_source = "NETWORK"
                    if request.cache_key is not None:
                        metrics.cache_update_start = Instant.now()
                        self.cache.store_http_response(
                            cache_key=request.cache_key, http_response=http_response
                        )
                        metrics.cache_update_end = Instant.now()
                        if cache_status == "STALE":
                            metrics.response_source = "NETWORK_STALE_CACHE_UPDATED"
                    metrics.request_end = Instant.now()
                    return EsiResponse(
                        request=request.esi_request,
                        http_response=http_response,
                        metrics=metrics,
                    )
                case 201:  # Created Successful
                    # TODO handle 201 Created responses if needed
                    raise NotImplementedError("201 Created handling not implemented.")
                    metrics.request_end = Instant.now()
                    metrics.response_source = "NETWORK"
                    return EsiResponse(
                        request=request.esi_request,
                        http_response=http_response,
                        metrics=metrics,
                    )
                case 204:  # No Content Successful
                    # TODO handle 204 No Content responses if needed
                    raise NotImplementedError(
                        "204 No Content handling not implemented."
                    )
                    metrics.request_end = Instant.now()
                    metrics.response_source = "NETWORK"
                    return EsiResponse(
                        request=request.esi_request,
                        http_response=http_response,
                        metrics=metrics,
                    )
                case 304:
                    if request.cache_key is None:
                        raise EsiLinkError("Received 304 but no cache is configured.")
                    metrics.cache_update_start = Instant.now()
                    self.cache.update_http_response(
                        cache_key=request.cache_key, http_response=http_response
                    )
                    metrics.cache_update_end = Instant.now()
                    cached_response = self.cache.get_cached_response(request.cache_key)
                    if cached_response is None:
                        raise EsiLinkError("Received 304 but no cached response found.")
                    metrics.request_end = Instant.now()
                    metrics.response_source = "NETWORK_STALE_CACHE_OK"
                    return EsiResponse(
                        request=request.esi_request,
                        http_response=http_response,
                        metrics=metrics,
                    )
                case 429:  # Rate Limited
                    raise NotImplementedError(
                        "429 Rate Limit handling not implemented."
                    )
                    raise EsiLinkError(
                        f"Rate limited on request to {http_response.url}. Retry after {metrics.retry_after} seconds."
                    )

                # FIXME limit the number of 400 errors before failing.
                case 400 | 401 | 403 | 404 | 500 | 502 | 503 | 504:
                    self._error_count += 1
                    raise EsiLinkError(
                        f"Error response {http_response.status_code} for URL {http_response.url}"
                    )
                case _:
                    logger.warning(
                        f"Unhandled status code {http_response.status_code} for URL {http_response.url}"
                    )
                    # TODO more specific error with code and reason as fields.
                    raise EsiLinkError(
                        f"Unhandled status code {http_response.status_code}, {http_response.reason} for URL {http_response.url}"
                    )
        except Exception as e:
            error_msg = f"Error processing request for URL {request.url}: {e!r}"
            logger.error(error_msg)

            return EsiResponse(
                request=request.esi_request,
                http_response=http_response,
                metrics=metrics,
                error_messages=[error_msg],
            )
        finally:
            metrics.request_end = Instant.now()
            logger.info(
                f"Request for URL {request.url} started at {metrics.request_start.format_iso()} "
                f"and ended at {metrics.request_end.format_iso()}. Took "
                f"{(metrics.request_end - metrics.request_start).in_seconds():.2f} seconds."
            )
            logger.info(f"Metrics: {metrics.model_dump_json()}")

    async def get_paged_response(
        self, request: HttpRequest, *, last_modified: str
    ) -> HttpResponse:
        """Fetch a single page of a multi page request and check for consistency."""
        try:
            http_response = await self.get_response(
                request, metrics=None, raise_for_status=True
            )
        except Exception as e:
            raise EsiLinkError(
                f"Failed to fetch paged data for URL {request.url}: {e}"
            ) from e
        if last_modified and http_response.last_modified != last_modified:
            raise EsiLinkError(
                f"Last-Modified mismatch for paged response at URL {http_response.url}, expected {last_modified}, got {http_response.last_modified}"
            )
        return http_response

    async def get_paged_data(
        self, *, request: HttpRequest, first_page: HttpResponse, metrics: Metrics
    ) -> None:
        """Complete a paged request by fetching 2->n pages.

        Paged data is combined into the first_page HttpResponse instance,
        which is modified in place. Paged requests are run in a TaskGroup,
        which allows for concurrent fetching of pages, and one failure will
        cause the entire group to fail.
        """
        metrics.pages_start = Instant.now()
        paged_requests = self.build_paged_requests(request, first_page)
        metrics.pages_required = len(paged_requests) + 1  # +1 for the first page
        logger.info(
            f"Fetching {len(paged_requests)} additional pages for paged request to URL {request.url} at {metrics.pages_start.format_iso()}."
        )
        coros = [
            self.get_paged_response(request, last_modified=first_page.last_modified)
            for request in paged_requests
        ]
        tasks: list[asyncio.Task[HttpResponse]] = []
        try:
            async with asyncio.TaskGroup() as tg:
                for coro in coros:
                    tasks.append(tg.create_task(coro))
        except* Exception as eg:
            raise EsiLinkError(
                f"Error fetching paged data for URL {request.url}: {eg}"
            ) from eg

        metrics.pages_end = Instant.now()
        logger.info(
            f"Completed fetching paged data for URL {request.url} at {metrics.pages_end.format_iso()} in {(metrics.pages_end - metrics.pages_start).in_seconds():.2f} seconds."
        )
        for task in tasks:
            http_response = task.result()
            # Merge the JSON data from the paged response into the first page
            if isinstance(first_page.json_data, list) and isinstance(  # pyright: ignore[reportUnknownMemberType]
                http_response.json_data, list
            ):
                first_page.json_data.extend(http_response.json_data)  # pyright: ignore[reportUnknownMemberType]
            elif isinstance(first_page.json_data, dict) and isinstance(  # pyright: ignore[reportUnknownMemberType]
                http_response.json_data, dict
            ):
                first_page.json_data.update(http_response.json_data)  # pyright: ignore[reportUnknownMemberType]
            else:
                logger.warning(
                    f"Cannot merge paged response data for URL {http_response.url}"
                )
        return None

    def build_paged_requests(
        self, request: HttpRequest, first_page: HttpResponse
    ) -> list[HttpRequest]:
        """Build a list of paged requests based on the first page response."""
        if not request.is_paged:
            raise EsiLinkError("Request is not marked as paged.")
        page_count = int(HF.pages_available(first_page.headers))
        if page_count < 1:
            raise EsiLinkError("Invalid page count retrieved from headers.")
        paged_requests: list[HttpRequest] = []
        if page_count == 1:
            return paged_requests
        for page_number in range(2, page_count + 1):
            paged_request = deepcopy(request)
            # Clear any user defined handlers for paged requests
            paged_request.esi_request.handlers = []
            paged_request.page_number = page_number
            # Update the URL to include the page parameter
            paged_request.esi_request.query_parameters["page"] = page_number
            paged_request.url = build_url(
                paged_request.esi_request,
                esi_schema=self.esi_schema,
            )
            paged_requests.append(paged_request)
        return paged_requests

    async def get_response(
        self,
        request: HttpRequest,
        *,
        metrics: Metrics | None,
        raise_for_status: bool = False,
    ) -> HttpResponse:
        """Get a single HTTP response.

        Use raise_for_status with paged requests, as all pages must complete successfully
        to be useful.

        Args:
            request: The HttpRequest instance to execute.
            metrics: The Metrics instance to update with request timing.
            raise_for_status: Whether to raise an exception for HTTP error status codes.

        Returns:
            A tuple of the HttpRequest and HttpResponse.
        """
        if not self.session:
            raise EsiLinkError("HTTP session is not initialized.")
        if metrics:
            metrics.response_start = Instant.now()
        if self._error_count >= 10:
            raise EsiLinkError("Too many errors encountered; aborting requests.")
        async with self.limiter:
            timeout_obj = aiohttp.ClientTimeout(total=request.timeout)
            async with self.session.request(
                method=request.method,
                url=request.url,
                headers=request.headers,
                timeout=timeout_obj,
                json=request.json_body,
            ) as response:
                if raise_for_status:
                    response.raise_for_status()
                if response.status == 304:
                    json_data = None
                else:
                    json_data = await response.json()
                logger.info(f"Response JSON data for URL {request.url}: {json_data!r}")
                http_response = HttpResponse(
                    status_code=response.status,
                    reason=response.reason,
                    url=str(response.url),
                    headers=tuple(response.headers.items()),
                    json_data=json_data,
                    etag=response.headers.get("ETag", ""),
                    last_modified=response.headers.get("Last-Modified", ""),
                    expires=response.headers.get("Expires", ""),
                )
                if metrics:
                    metrics.response_end = Instant.now()
                return http_response

    async def execute_requests(
        self,
        requests: list[HttpRequest],
    ) -> list[EsiResponse]:
        """Execute a list of HTTP requests.

        Gathers all request coroutines and executes them concurrently.
        Entering here prevents wrapping the coros, e.g. for response handlers.

        Args:
            requests: A list of HttpRequest instances to execute.

        Returns:
            A list of EsiResponse instances.
        """
        request_coros = await self.collect_request_coros(requests)
        results = await asyncio.gather(*request_coros)
        return results

    async def collect_request_coros(
        self, requests: list[HttpRequest]
    ) -> list[CoroutineType[Any, Any, EsiResponse]]:
        """Collect coroutines for executing HTTP requests.

        Gathers all request coroutines. Can be used to execute requests in a custom manner.
        e.g., Wrapping the coros in response handlers, etc.

        Args:
            requests: A list of HttpRequest instances to execute.

        Returns:
            A list of coroutine objects for the given HTTP requests.
        """
        request_coros = [self._worker(req) for req in requests]
        return request_coros


def metrics_rate_limits(metrics: Metrics, http_response: HttpResponse) -> None:
    """Update metrics with rate limit information from the HTTP response headers."""
    metrics.ratelimit_group = HF.ratelimit_group(http_response.headers)
    metrics.ratelimit_limit = HF.ratelimit_limit(http_response.headers)
    metrics.ratelimit_remaining = HF.ratelimit_remaining(http_response.headers)
    metrics.ratelimit_used = HF.ratelimit_used(http_response.headers)
    metrics.retry_after = HF.retry_after(http_response.headers)
