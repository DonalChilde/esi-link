import asyncio
import logging
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from types import TracebackType
from typing import Any, Optional
from uuid import NAMESPACE_URL, UUID, uuid5

import aiohttp
from aiolimiter import AsyncLimiter
from whenever import Instant

from esi_link import operation_accessors as OA
from esi_link.helpers import header_funcs as HF
from esi_link.models import (
    CachedResponse,
    CacheProtocol,
    EsiHttpProtocol,
    EsiLinkError,
    EsiLinkProtocol,
    EsiRequest,
    EsiRequests,
    EsiSchema,
    HandlerConfig,
    HandlerManagerProtocol,
    HandlerNotFoundError,
    HttpRequest,
    HttpResponse,
    InvalidHandlerError,
    ResponseContext,
    ResponseHandlerProtocol,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
ESI_LINK_NAMESPACE = uuid5(NAMESPACE_URL, "esi-link")


###########################################################################
# Helpers
###########################################################################
def build_url(
    esi_request: EsiRequest,
    esi_schema: EsiSchema,
    base_url: str = "",
) -> str:
    """Build the full URL for an ESI request using the ESI schema.

    Args:
        esi_request: The EsiRequest instance containing the operation ID and parameters.
        esi_schema: The EsiSchema instance containing the OpenAPI schema.

    Returns:
        The full URL as a string.
    """
    operation = esi_schema.operations.get(esi_request.operation_id)
    base_url = base_url or esi_schema.servers[0]["url"]
    if not operation:
        raise EsiLinkError(f"Operation ID not found: {esi_request.operation_id}")
    path_params = esi_request.path_parameters or {}
    query_params = esi_request.query_parameters or {}
    path_template = operation.path
    path = path_template.format(**path_params)
    resolved_url = f"{base_url.strip('/')}/{path.strip('/')}"
    # Construct the query string from the query parameters
    # Sort keys so URL is stable regardless of dict insertion order
    query_items = sorted(query_params.items(), key=lambda kv: kv[0])
    query_string = "&".join([f"{key}={value}" for key, value in query_items])
    # Combine the path and query string into the final URL
    return f"{resolved_url}?{query_string}" if query_string else resolved_url


def generate_cache_key(esi_request: EsiRequest, esi_schema: EsiSchema) -> UUID | None:
    """Generate a cache key for the given ESI request.

    Args:
        esi_request: The EsiRequest instance for which to generate the cache key.
        esi_schema: The EsiSchema instance containing the OpenAPI schema.
    Returns:
        A UUID representing the cache key, or None if caching is not applicable.
    """
    indexed_operation = esi_schema.operations.get(esi_request.operation_id)
    if not indexed_operation:
        raise EsiLinkError(f"Operation ID not found: {esi_request.operation_id}")
    if indexed_operation.method != "GET":
        return None
    # Build a unique string representation of the request
    key_string = f"{indexed_operation.method}:{indexed_operation.operation_id}"
    if esi_request.path_parameters:
        sorted_path_params = sorted(esi_request.path_parameters.items())
        path_params_str = ",".join(f"{k}={v}" for k, v in sorted_path_params)
        key_string += f":{path_params_str}"
    if esi_request.query_parameters:
        sorted_query_params = sorted(esi_request.query_parameters.items())
        query_params_str = ",".join(f"{k}={v}" for k, v in sorted_query_params)
        key_string += f"?{query_params_str}"
    # Generate a UUID based on the key string within the ESI_LINK_NAMESPACE
    cache_key = uuid5(ESI_LINK_NAMESPACE, key_string)
    return cache_key


###########################################################################
# Implementations
###########################################################################

###########################################################################
# CacheProtocol Implementations
###########################################################################


class NoOpCache(CacheProtocol):
    """A no-op cache implementation that does not store any responses."""

    def generate_cache_key(
        self, esi_request: EsiRequest, esi_schema: EsiSchema
    ) -> UUID | None:
        return None

    def is_cached(self, cache_key: UUID) -> bool:
        return False

    def get_cached_response(self, cache_key: UUID) -> Optional[CachedResponse]:
        return None

    def store_cached_response(self, cached_response: CachedResponse) -> None:
        pass

    def update_cached_response(
        self, cache_key: UUID, http_response: HttpResponse
    ) -> None:
        pass


class InMemoryCache(CacheProtocol):
    """An in-memory cache implementation for storing ESI responses."""

    def __init__(self) -> None:
        self.cache: dict[UUID, CachedResponse] = {}

    def generate_cache_key(
        self, esi_request: EsiRequest, esi_schema: EsiSchema
    ) -> UUID | None:
        cache_key = generate_cache_key(esi_request=esi_request, esi_schema=esi_schema)
        return cache_key

    def is_cached(self, cache_key: UUID) -> bool:
        return cache_key in self.cache

    def get_cached_response(self, cache_key: UUID) -> Optional[CachedResponse]:
        return self.cache.get(cache_key)

    def store_cached_response(self, cached_response: CachedResponse) -> None:
        self.cache[cached_response.cache_key] = cached_response

    def update_cached_response(
        self, cache_key: UUID, http_response: HttpResponse
    ) -> None:
        if cache_key in self.cache:
            cached_response = self.cache[cache_key]
            cached_response.response = http_response
            cached_response.cached_on = Instant.now()
            self.cache[cache_key] = cached_response


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
        time_period: int = 60,
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
        start = perf_counter()
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
            _, http_response = await self.get_response(request=request)
            match http_response.status_code:
                case 200:
                    if request.is_paged:
                        await self.get_paged_data(
                            request=request, first_page=http_response
                        )
                    if request.cache_key is not None:
                        cached_response = CachedResponse(
                            cache_key=request.cache_key, response=http_response
                        )
                        self.cache.store_cached_response(cached_response)
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
                    self.cache.update_cached_response(request.cache_key, http_response)
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
            return (request, e)
        finally:
            logger.info(
                f"Processed request for URL {request.url} in {perf_counter() - start:.2f} seconds."
            )

    async def get_paged_data(
        self, request: HttpRequest, first_page: HttpResponse
    ) -> None:
        """Complete a paged request by fetching all pages."""
        paged_requests = self.build_paged_requests(request, first_page)
        tasks = [self.get_response(req) for req in paged_requests]
        results = await asyncio.gather(*tasks)
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


###########################################################################
# EsiLinkProtocol Implementations
###########################################################################


class EsiLink(EsiLinkProtocol):
    """Default implementation of the EsiLinkProtocol.

    This implementation uses aiohttp to execute ESI requests and process responses.
    """

    def __init__(
        self,
        esi_schema: EsiSchema,
        esi_http: EsiHttpProtocol,
        handler_manager: HandlerManagerProtocol,
    ) -> None:
        self.esi_schema = esi_schema
        self.esi_http = esi_http
        self.handler_manager = handler_manager

        app_handler_configs = self.app_handler_configs()
        self.app_handlers: list[ResponseHandlerProtocol] = self.init_handlers(
            app_handler_configs
        )

    def app_handler_configs(self) -> list[HandlerConfig]:
        """Get the application-level handler configurations.

        This method should be implemented to return the list of HandlerConfig
        instances that define the application-level response handlers.

        Returns:
            A list of HandlerConfig instances.
        """
        # TODO define a list of app handler configs.
        return []

    def init_handlers(
        self, handler_configs: list[HandlerConfig]
    ) -> list[ResponseHandlerProtocol]:
        """Initialize application-level response handlers."""

        app_handlers = [
            self.handler_manager.get_handler(config) for config in handler_configs
        ]
        return app_handlers

    async def execute_requests(
        self,
        ctx: ResponseContext,
        requests: EsiRequests,
    ) -> None:
        # Build HttpRequest objects from EsiRequest objects
        http_requests: list[HttpRequest] = []
        for req in requests.requests.values():
            url = build_url(req, self.esi_schema)
            indexed_operation = self.esi_schema.operations.get(req.operation_id)
            if not indexed_operation:
                raise EsiLinkError(f"Operation ID not found: {req.operation_id}")
            user_handlers = self.init_handlers(req.handlers)
            is_paged = OA.is_paged(indexed_operation)
            http_request = HttpRequest(
                method=indexed_operation.method,
                url=url,
                ctx=ctx,
                esi_request=req,
                cache_key=self.esi_http.cache.generate_cache_key(
                    esi_request=req, esi_schema=self.esi_schema
                ),
                app_handlers=self.app_handlers,
                user_handlers=user_handlers,
                headers=req.headers,
                is_paged=is_paged,
            )
            http_requests.append(http_request)
            async with self.esi_http as http_client:
                await http_client.execute_requests(http_requests)
        return None


###########################################################################
# ResponseHandlerProtocol Implementations
###########################################################################


class JsonFileResponseHandler(ResponseHandlerProtocol):
    """A response handler that saves the JSON response to a file."""

    name: str = "esi-link.json_data_file"

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    async def handle_response(
        self,
        ctx: ResponseContext,
        http_response: HttpResponse,
        request: EsiRequest,
    ) -> None:
        if http_response.json_data is not None:
            path_out = Path(self._file_path.format(**self.tokens(request)))
            path_out.parent.mkdir(parents=True, exist_ok=True)
            with open(path_out, "w") as file:
                import json

                json.dump(http_response.json_data, file, indent=2)

    def tokens(self, request: EsiRequest) -> dict[str, str]:
        token_values = {
            "operation_id": request.operation_id,
            "query_id": str(request.query_id),
            "now": Instant.now().format_iso(),
        }
        token_values.update(
            {key: str(value) for key, value in request.path_parameters.items()}
        )
        token_values.update(
            {key: str(value) for key, value in request.query_parameters.items()}
        )
        if request.auth_parameters:
            token_values.update(
                {
                    "character_id": str(request.auth_parameters.character_id),
                    "client_id": str(request.auth_parameters.client_id),
                    "client_alias": request.auth_parameters.client_alias,
                }
            )
        return token_values

    @classmethod
    def from_config(cls, config: HandlerConfig) -> "JsonFileResponseHandler":
        file_path_str = config.config.get("file_path")
        if not file_path_str:
            raise InvalidHandlerError("file_path is required in handler config.")
        return cls(file_path=file_path_str)

    @classmethod
    def example_config(cls) -> tuple[HandlerConfig, str]:
        """Return an example configuration for this handler, with a text description.

        Example does not have to be a valid config, but should illustrate the main options.
        """
        example = HandlerConfig(
            name=cls.name,
            config={"file_path": "responses/{operation_id}-response.json"},
        )
        description = (
            "Saves the JSON response to the specified file path. "
            "The file_path option is required. file_path supports str.format replacement "
            "with tokens for operation_id, query_id, now, and any path, query or auth parameters."
        )
        return example, description

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        if "file_path" not in config.config:
            raise InvalidHandlerError("file_path is required in handler config.")
        if not config.name.startswith("esi-link."):
            raise InvalidHandlerError(
                "Handler name must be in the 'esi-link.' namespace."
            )


class HandlerManager(HandlerManagerProtocol):
    """A simple handler manager implementation."""

    def __init__(self) -> None:
        self.handlers: dict[str, type[ResponseHandlerProtocol]] = {}

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        handler_cls = self.handlers.get(config.name)
        if not handler_cls:
            raise HandlerNotFoundError(f"Handler not found: {config.name}")
        return handler_cls.from_config(config)

    def register_handler(
        self, name: str, handler_cls: type[ResponseHandlerProtocol]
    ) -> None:
        if not issubclass(handler_cls, ResponseHandlerProtocol):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise InvalidHandlerError(
                f"Handler class must implement ResponseHandlerProtocol: {name}"
            )
        self.handlers[name] = handler_cls


class LinkManager:
    """Handles the initialization and management of EsiLink instances."""

    def __init__(
        self,
        esi_schema: dict[str, Any],
        schema_download_date: Instant,
    ) -> None:
        self.esi_schema = EsiSchema.from_schema(
            schema=esi_schema, download_date=schema_download_date
        )
        self._handler_manager = self.get_handler_manager()

    def get_handler_manager(self) -> HandlerManagerProtocol:
        handler_manager = HandlerManager()
        handler_manager.register_handler(
            JsonFileResponseHandler.name, JsonFileResponseHandler
        )
        return handler_manager

    def esi_link_factory(self) -> EsiLinkProtocol:
        cache = InMemoryCache()
        esi_http = EsiHttpRateLimited(cache=cache, esi_schema=self.esi_schema)
        esi_link = EsiLink(
            esi_schema=self.esi_schema,
            esi_http=esi_http,
            handler_manager=self._handler_manager,
        )
        return esi_link
