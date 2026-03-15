from types import TracebackType
from typing import Any, Protocol, Self
from uuid import UUID

from esi_link.models_2 import (
    CachedResponse,
    CachedResponseStatus,
    GeneratedUrlInfo,
    HttpResponse,
    Request,
    RequestGroup,
    Response,
    ResponseGroup,
    ResponseGroupHandlerConfig,
    ResponseHandlerConfig,
    RuntimeRequest,
)


class HttpRequestExecutorProtocol(Protocol):
    def __call__(self, request: Request) -> Response: ...


class RequestGroupExecutorProtocol(Protocol):
    def __call__(self, request_group: RequestGroup) -> ResponseGroup: ...


class RuntimeRequestGenerator(Protocol):
    def __call__(self, request: Request) -> RuntimeRequest: ...


class RequestValidatiorProtocol(Protocol):
    def __call__(self, request: Request) -> None:
        """Validate a request.

        Raises:
            RequestValidationError
        """
        ...


class RequestGroupValidatorProtocol(Protocol):
    def __call__(self, request_group: RequestGroup) -> None:
        """Validate a RequestGroup.

        Raises:
            RequestValidationError
        """
        ...


class ResponseHandlerProtocol(Protocol):
    def __call__(self, response: Response) -> Response: ...


class ResponseGroupHandlerProtocol(Protocol):
    def __call__(self, response_group: ResponseGroup) -> ResponseGroup: ...


class ResponseHandlerManagerProtocol(Protocol):
    def get_handler(self, config: ResponseHandlerConfig) -> ResponseHandlerProtocol: ...


class ResponseGroupHandlerManagerProtocol(Protocol):
    def get_handler(
        self, config: ResponseGroupHandlerConfig
    ) -> ResponseGroupHandlerProtocol: ...


class CacheManagerProtocol:
    def __enter__(self) -> Self:
        """Enter the runtime context related to this object."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the runtime context related to this object."""
        ...

    def get(
        self, key: UUID, local_max_age: int | None = None
    ) -> tuple[CachedResponse | None, CachedResponseStatus]:
        """Get a cached response by cache key.

        Local max age allows the caller to specify a max age for staleness that is
        different from the max age received from the server.

        Returned CachedResponse must be treated as immutable. If the caller needs to
        modify the CachedResponse, they should create a copy of it before making any
        modifications, to avoid unintended side effects on the cached response stored in
        the cache manager. Modifying the returned CachedResponse directly may lead to
        issues such as stale data being returned for other requests that share the same
        cache key, or inconsistencies in the cache state if the CachedResponse is updated
        with new data while it is being modified by the caller.

        Args:
            key: The UUID key for the cached response.
            local_max_age: The maximum age of the cached response in seconds. If the cached
                response is older than this, it will be considered stale.

        Returns:
            A tuple containing the CachedResponse if found, or None if not found, and
                the CachedResponseStatus.
        """
        ...

    def set(self, key: UUID, http_response: HttpResponse) -> CachedResponse:
        """Set a cached response in the cache.

        Returned CachedResponse must be treated as immutable. If the caller needs to
        modify the CachedResponse, they should create a copy of it before making any
        modifications, to avoid unintended side effects on the cached response stored in
        the cache manager. Modifying the returned CachedResponse directly may lead to
        issues such as stale data being returned for other requests that share the same
        cache key, or inconsistencies in the cache state if the CachedResponse is updated
        with new data while it is being modified by the caller.

        Args:
            key: The UUID key for the cached response.
            http_response: The new HttpResponse to store in the cache.

        Returns:
            The CachedResponse instance that was set in the cache.
        """
        ...

    def refresh(self, key: UUID, new_http_response: HttpResponse) -> CachedResponse:
        """Refresh an existing cached response with new response data.

        Returned CachedResponse must be treated as immutable. If the caller needs to
        modify the CachedResponse, they should create a copy of it before making any
        modifications, to avoid unintended side effects on the cached response stored in
        the cache manager. Modifying the returned CachedResponse directly may lead to
        issues such as stale data being returned for other requests that share the same
        cache key, or inconsistencies in the cache state if the CachedResponse is updated
        with new data while it is being modified by the caller.

        Args:
            key: The UUID key for the cached response to refresh.
            new_http_response: The new HttpResponse to update the cached response with.

        Returns:
            The updated CachedResponse instance after refreshing.

        Raises:
            KeyError: If no cached response exists for the given cache key.
        """
        ...

    def clear(self, only_stale: bool = False) -> int:
        """Clear all cached responses from the cache.

        Args:
            only_stale: If True, only clear stale cached responses.

        Returns:
            The number of cached responses that were cleared.
        """
        ...

    def cache_info(self) -> dict[str, Any]:
        """Get information about the cache, such as size, number of entries, etc.

        Returns:
            A dictionary containing information about the cache.
        """
        ...


class UrlGeneratorProtocol:
    def generate_path_url(self, request: Request) -> str:
        """Generate the url path for an ESI request based on its parameters.\
            
        This url does not contain query parameters, and is not suitable for generateing 
        a cache key. It is used as the url argument for http requests, assuming that 
        query parameters are sent separately.
        """
        ...

    def generate_cache_url(self, request: Request) -> str:
        """Generate the url to use for cache key generation for an ESI request based on its parameters.

        This url should contain all path and most query parameters, and should be
        consistent for requests that should share a cache key. It is used for generating
        cache keys, and is not necessarily the same as the url used for making the http request.

        NOTE: Validate the request before generating the cache url, to ensure that all
        required parameters are present and correctly formatted, to avoid generating
        different cache urls for requests that should share a cache key.
        """
        ...

    def generate_cache_key(self, request: Request) -> UUID:
        """Generate a cache key for an ESI request based on its parameters.

        The key is usually generated by hashing the url generated by generate_cache_url,
        but can be any UUID that is consistently generated for requests that should share
        a cache key.
        """
        ...

    def generate_url_info(self, request: Request) -> GeneratedUrlInfo:
        """Generate all url related information for an ESI request.

        This is a convenience method that generates the path url, cache url, and cache key
        for an ESI request in one call, since these values are often needed together
        and share intermediate calculations.

        NOTE: Validate the request before generating the cache url, to ensure that all
        required parameters are present and correctly formatted, to avoid generating
        different cache urls for requests that should share a cache key.
        """
        ...
