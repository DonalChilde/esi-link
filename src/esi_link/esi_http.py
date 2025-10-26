import asyncio
import logging
from copy import deepcopy
from types import TracebackType

import aiohttp
from aiolimiter import AsyncLimiter
from whenever import Instant

from esi_link import header_funcs as HF
from esi_link.build_url import build_url
from esi_link.models import (
    CacheProtocol,
    EsiHttpProtocol,
    EsiLinkError,
    EsiSchema,
    HttpRequest,
    HttpResponse,
)

logger = logging.getLogger(__name__)
###########################################################################
# EsiHttpProtocol Implementations
###########################################################################


class EsiHttpRateLimited(EsiHttpProtocol):
    """An ESI HTTP client implementation that collects requests and processes them asynchronously."""

    def __init__(
        self,
        cache: CacheProtocol,
        esi_schema: EsiSchema,
        max_rate: int = 100,
        time_period: float = 60.0,
    ) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.cache = cache
        self.esi_schema = esi_schema
        self.max_rate = max_rate
        self.time_period = time_period
        self._error_count: int = 0

    async def __aenter__(self) -> "EsiHttpRateLimited":
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
        assert self.session is not None, "Session is not initialized."
        await self.session.close()

    async def _do_handlers(
        self, request: HttpRequest, http_response: HttpResponse
    ) -> None:
        # Process app level handlers
        for handler in request.app_handlers:
            await handler.handle_response(
                request.ctx, http_response, request.esi_request
            )
        # Process user level handlers
        for handler in request.user_handlers:
            await handler.handle_response(
                request.ctx, http_response, request.esi_request
            )

    async def _worker(
        self, request: HttpRequest
    ) -> tuple[HttpRequest, BaseException | None]:
        """Worker to process a single HTTP request.

        Args:
            request: The HttpRequest instance to process.

        Returns:
            A tuple of the HttpRequest and either None or an exception if one occurred.
        """
        # TODO log rate limit info
        worker_start = Instant.now()
        try:
            if not self.session:
                raise EsiLinkError("HTTP session is not initialized.")
            if request.cache_key is not None:
                cached_response = self.cache.get_cached_response(request.cache_key)
                if cached_response is not None and not cached_response.is_stale():
                    await self._do_handlers(request, cached_response.response)
                    return (request, None)
                if cached_response is not None and cached_response.is_stale():
                    # Add conditional headers to the request
                    # Use ETag and Last-Modified from the cached response
                    if cached_response.response.etag:
                        request.headers["If-None-Match"] = cached_response.response.etag
                    if cached_response.response.last_modified:
                        request.headers["If-Modified-Since"] = (
                            cached_response.response.last_modified
                        )
            request_start = Instant.now()
            _, http_response = await self.get_response(request=request)
            request_end = Instant.now()
            logger.info(
                f"Processed http request for URL {request.url} in {(request_end - request_start).in_seconds():.2f} seconds."
            )
            match http_response.status_code:
                case 200:
                    if request.is_paged:
                        await self.get_paged_data(
                            request=request, first_page=http_response
                        )
                    if request.cache_key is not None:
                        self.cache.store_http_response(
                            cache_key=request.cache_key, http_response=http_response
                        )
                    await self._do_handlers(request, http_response)
                    return (request, None)
                case 201:  # Created Successful
                    # TODO handle 201 Created responses if needed
                    await self._do_handlers(request, http_response)
                    return (request, None)
                case 204:  # No Content Successful
                    # TODO handle 204 No Content responses if needed
                    await self._do_handlers(request, http_response)
                    return (request, None)
                case 304:
                    if request.cache_key is None:
                        raise EsiLinkError("Received 304 but no cache is configured.")
                    self.cache.store_http_response(
                        cache_key=request.cache_key, http_response=http_response
                    )
                    cached_response = self.cache.get_cached_response(request.cache_key)
                    if cached_response is None:
                        raise EsiLinkError("Received 304 but no cached response found.")
                    await self._do_handlers(request, cached_response.response)
                    return (request, None)
                case 429:  # Rate Limited
                    # TODO consider retry logic here.
                    retry_after = HF.retry_after(http_response.headers)
                    raise EsiLinkError(
                        f"Rate limited on request to {http_response.url}. Retry after {retry_after} seconds."
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
            logger.error(f"Error processing request for URL {request.url}: {e}")
            request.ctx.response_data.exceptions[request.esi_request.request_id] = (  # pyright: ignore[reportArgumentType]
                request,
                e,
            )
            return (request, e)
        finally:
            worker_end = Instant.now()
            logger.info(
                f"Request for URL {request.url} started at {worker_start.format_iso()} and ended at {worker_end.format_iso()}. Took {(worker_end - worker_start).in_seconds():.2f} seconds."
            )

    async def get_paged_data(
        self, request: HttpRequest, first_page: HttpResponse
    ) -> None:
        """Complete a paged request by fetching all pages.

        Paged data is combined into the first_page HttpResponse instance,
        which is modified in place. Finally, handlers are run on the combined response.
        """
        paged_requests = self.build_paged_requests(request, first_page)
        paged_start = Instant.now()
        logger.info(
            f"Fetching {len(paged_requests)} additional pages for paged request to URL {request.url} at {paged_start.format_iso()}."
        )
        tasks = [self.get_response(req) for req in paged_requests]
        results = await asyncio.gather(*tasks)
        paged_end = Instant.now()
        logger.info(
            f"Completed fetching paged data for URL {request.url} at {paged_end.format_iso()} in {(paged_end - paged_start).in_seconds():.2f} seconds."
        )
        for result in results:
            _, http_response = result
            if http_response.status_code != 200:
                raise EsiLinkError(
                    f"Failed to fetch paged data for URL {http_response.url} with status code {http_response.status_code}"
                )
            if first_page.etag and http_response.etag != first_page.etag:
                raise EsiLinkError(
                    f"ETag mismatch for paged response at URL {http_response.url}"
                )
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
        # After all pages are fetched and merged, run handlers on the combined response
        await self._do_handlers(request, first_page)
        return None

    def build_paged_requests(
        self, request: HttpRequest, first_page: HttpResponse
    ) -> list[HttpRequest]:
        """Build a list of paged requests based on the first page response."""

        if not request.is_paged:
            raise EsiLinkError("Request is not marked as paged.")
        page_count = HF.pages_available(first_page.headers)
        if page_count < 1:
            raise EsiLinkError("Invalid page count retrieved from headers.")
        http_requests: list[HttpRequest] = []
        if page_count == 1:
            return http_requests
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
            http_requests.append(paged_request)
        return http_requests

    async def get_response(
        self, request: HttpRequest
    ) -> tuple[HttpRequest, HttpResponse]:
        """Get a single HTTP response.

        Args:
            request: The HttpRequest instance to execute.

        Returns:
            A tuple of the HttpRequest and HttpResponse.
        """
        if not self.session:
            raise EsiLinkError("HTTP session is not initialized.")
        if self._error_count >= 10:
            raise EsiLinkError("Too many errors encountered; aborting requests.")
        async with self.limiter:
            timeout_obj = aiohttp.ClientTimeout(total=request.timeout)
            async with self.session.request(
                method=request.method,
                url=request.url,
                headers=request.headers,
                timeout=timeout_obj,
            ) as response:
                http_response = HttpResponse(
                    status_code=response.status,
                    reason=response.reason,
                    url=str(response.url),
                    headers=tuple(response.headers.items()),
                    json_data=await response.json(),
                    etag=response.headers.get("ETag", ""),
                    last_modified=response.headers.get("Last-Modified", ""),
                    expires=response.headers.get("Expires", ""),
                )
                return (request, http_response)

    async def execute_requests(
        self,
        requests: list[HttpRequest],
    ) -> list[tuple[HttpRequest, BaseException | None]]:
        """Execute a list of HTTP requests.

        Args:
            requests: A list of HttpRequest instances to execute.
        Returns:
            A list of tuples containing the HttpRequest and either None or an exception if one occurred.
        """

        tasks = [self._worker(req) for req in requests]
        results = await asyncio.gather(*tasks)
        return results
