from dataclasses import dataclass, field
from typing import Any, Self
from uuid import UUID

import aiohttp
from pydantic import BaseModel, Field
from whenever import Instant

from esi_link.v2.helpers.pydantic.save_to_disk import BaseModelToDisk
from esi_link.v2.helpers.resolve_json_ref import resolve_internal_refs


def _get_current_instant() -> Instant:
    """Factory function to get current instant for default values.

    This function is used as a default_factory to avoid circular dependencies
    that can occur when using Instant.now directly in field definitions.

    Returns:
        Current instant in time.
    """
    return Instant.now()


class HandlerConfig(BaseModel):
    """Configuration for a response handler."""

    name: str
    """Name of the handler. Handler names are namespaced. The esi-link.foo namespace is reserved."""
    config: dict[str, Any] = {}
    """Configuration specific to the handler."""


class AuthParameters(BaseModel):
    """Authentication parameters for an ESI request."""

    character_id: int
    client_alias: str
    """Alias for the client credentials to use for authentication."""


class RuntimeRequestInfo(BaseModel):
    """Represents the runtime information needed for an EsiRequest."""

    url: str
    method: str
    is_paged: bool = False
    is_auth: bool = False
    headers: dict[str, str] = {}
    """Includes UserAgent, and auth if required."""
    timeout: int = 10
    cache_key: UUID | None = None
    """Cache key for the request, if applicable. This is used to identify cached responses."""


class EsiRequest(BaseModelToDisk):
    """Represents a single ESI request to be executed."""

    request_id: UUID
    operation_id: str
    path_parameters: dict[str, str | int | float] = {}
    query_parameters: dict[str, str | int | float] = {}
    auth_parameters: AuthParameters | None = None
    body: Any | None = None
    headers: dict[str, str] = {}
    response_handlers: list[HandlerConfig] = []
    runtime_info: RuntimeRequestInfo | None = None


class EsiRequests(BaseModelToDisk):
    """Represents a batch of ESI requests to be executed."""

    created_on: Instant = Field(default_factory=_get_current_instant)
    requests_id: UUID
    description: str = ""
    requests: dict[UUID, EsiRequest]


class ResponseData(BaseModel):
    """Represents the data of an ESI response."""

    status_code: int
    headers: dict[str, str] = {}
    body: Any | None = None
    received_at: Instant = Field(default_factory=_get_current_instant)

    @property
    def etag(self) -> str | None:
        """Extract the ETag from the response headers, if present."""
        return (
            self.headers.get("ETag")
            or self.headers.get("Etag")
            or self.headers.get("etag")
        )

    @property
    def last_modified(self) -> str | None:
        """Extract the Last-Modified header from the response headers, if present."""
        return (
            self.headers.get("Last-Modified")
            or self.headers.get("Last-modified")
            or self.headers.get("last-modified")
        )

    @property
    def expires(self) -> str | None:
        """Extract the Expires header from the response headers, if present."""
        return self.headers.get("Expires") or self.headers.get("expires")


@dataclass(slots=True)
class Metrics:
    """Performance metrics for an esi request."""

    pass


class EsiResponse(BaseModelToDisk):
    """Represents the response from an ESI request."""

    request_id: UUID
    response_data: ResponseData | None = None
    metrics: Metrics | None = None
    exceptions: list[type[Exception]] = []


class CachedResponse(BaseModelToDisk):
    """Represents a cached response for an ESI request."""

    cache_key: UUID
    cached_on: Instant = Field(default_factory=_get_current_instant)
    """The instant when the response was cached."""
    response_data: ResponseData


@dataclass(slots=True)
class IndexedOperation:
    operation_id: str
    method: str
    path: str
    operation: dict[str, Any] = field(default_factory=dict[str, Any])


class IndexedEsiSchema(BaseModelToDisk):
    """Represents the entire schema for ESI requests and responses, indexed for efficient access."""

    download_date: Instant
    """The date the schema was downloaded."""
    operations: dict[str, IndexedOperation] = Field(default_factory=dict)
    """A mapping of operation IDs to IndexedOperation instances."""
    security_schemes: dict[str, Any] = Field(default_factory=dict)
    """A mapping of security scheme names to their definitions."""
    info: dict[str, Any] = Field(default_factory=dict)
    """The info section of the OpenAPI schema."""
    openapi: str
    """The OpenAPI version."""
    servers: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    """The servers section of the OpenAPI schema."""
    tags: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    """The tags section of the OpenAPI schema."""

    def __str__(self) -> str:
        """String representation of the IndexedEsiSchema instance."""
        return (
            f"IndexedEsiSchema(openapi={self.openapi}, operations={len(self.operations)}, "
            f"download_date={self.download_date})"
        )

    @classmethod
    def from_raw_schema(
        cls, raw_schema: dict[str, Any], download_date: Instant
    ) -> Self:
        """Factory method to create an IndexedEsiSchema instance from a raw OpenAPI schema.

        Args:
            raw_schema: The raw OpenAPI schema as a dictionary.
            download_date: The date the schema was downloaded.

        Returns:
            An instance of IndexedEsiSchema.
        """
        dereferenced_schema = resolve_internal_refs(raw_schema, raw_schema)

        operations: dict[str, IndexedOperation] = {}
        paths = dereferenced_schema.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                operation_id = operation.get("operationId")
                if operation_id:
                    operations[operation_id] = IndexedOperation(
                        operation_id=operation_id,
                        method=method.upper(),
                        path=path,
                        operation=operation,
                    )
        return cls(
            download_date=download_date,
            operations=operations,
            security_schemes=dereferenced_schema.get("components", {}).get(
                "securitySchemes", {}
            ),
            info=dereferenced_schema.get("info", {}),
            openapi=dereferenced_schema.get("openapi", ""),
            servers=dereferenced_schema.get("servers", []),
            tags=dereferenced_schema.get("tags", []),
        )


# --------------------------------------------------------------------------------------
# Protocols and Exceptions
# --------------------------------------------------------------------------------------


class HandlerException(Exception):
    """Base exception class for response handler errors."""

    def __init__(self, message: str, config: dict[str, Any]):
        super().__init__(message)
        self.config = config


class InvalidHandlerError(HandlerException):
    """Exception raised when a response handler configuration is invalid."""

    def __init__(self, message: str, config: dict[str, Any]):
        super().__init__(message, config)


class HandlerNotFoundError(HandlerException):
    """Exception raised when a response handler is not found."""

    def __init__(self, message: str, config: dict[str, Any]):
        super().__init__(message, config)


class HandlerExecutionError(HandlerException):
    """Exception raised when a response handler fails during execution."""

    def __init__(self, message: str, config: dict[str, Any]):
        super().__init__(message, config)


class ResponseHandlerProtocol:
    """Protocol for response handlers."""

    name: str
    config: dict[str, Any]
    """The HandlerConfig used to create the handler instance."""

    def handle_response(self, response: EsiResponse) -> None:
        """Handle the given ESI response.

        Args:
            response: The EsiResponse to handle.

        Raises:
            HandlerExecutionError: If an error occurs during handling.
        """
        ...

    @classmethod
    def from_config(cls, config: HandlerConfig) -> Self:
        """Factory method to create a handler instance from a HandlerConfig.

        Args:
            config: The HandlerConfig instance containing the configuration for the handler.

        Raises:
            InvalidHandlerError: If the configuration is invalid for this handler.
        """
        ...

    @classmethod
    def example_config(cls) -> tuple[HandlerConfig, str]:
        """Return an example configuration for this handler, with a text description.

        Example does not have to be a valid config, but should illustrate the main options.
        """
        ...

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        """Validate the handler configuration.

        Args:
            config: The HandlerConfig instance containing the configuration.

        Raises:
            InvalidHandlerError: If the configuration is invalid.
        """
        ...


class HandlerManagerProtocol:
    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        """Get a handler by config.

        Args:
            config: The HandlerConfig instance containing the configuration.

        Returns:
            An instance of the handler.

        Raises:
            HandlerNotFoundError: If the handler is not found.
        """
        ...

    def register_handler(
        self, name: str, handler_cls: type[ResponseHandlerProtocol]
    ) -> None:
        """Register a handler class with a name.

        Validates the handler class before registering.

        Args:
            name: The name of the handler.
            handler_cls: The handler class to register.

        Raises:
            InvalidHandlerError: If the handler class is invalid.
        """
        ...

    def get_all_handlers(self) -> list[type[ResponseHandlerProtocol]]:
        """Get a list of all registered handlers.

        Returns:
            A list of all registered handler instances.
        """
        ...


class CacheManagerProtocol:
    def get_cached_response(self, cache_key: UUID) -> CachedResponse | None:
        """Get a cached response by cache key.

        Args:
            cache_key: The UUID key for the cached response.

        Returns:
            The CachedResponse if found, or None if not found.
        """
        ...

    def set_cached_response(self, cached_response: CachedResponse) -> None:
        """Set a cached response in the cache.

        Args:
            cached_response: The CachedResponse instance to store in the cache.
        """
        ...

    def refresh_cached_response(
        self, cache_key: UUID, new_response_data: ResponseData
    ) -> None:
        """Refresh an existing cached response with new response data.

        Args:
            cache_key: The UUID key for the cached response to refresh.
            new_response_data: The new ResponseData to update the cached response with.

        Raises:
            KeyError: If no cached response exists for the given cache key.
        """
        ...


class RequestExecutionException(Exception):
    """Exception raised when an error occurs during ESI request execution."""

    def __init__(self, message: str, request: EsiRequest):
        super().__init__(message)
        self.request = request


class EsiRequestExecutorProtocol:
    async def execute_request(
        self, request: EsiRequest, session: aiohttp.ClientSession
    ) -> tuple[EsiRequest, EsiResponse]:
        """Execute an ESI request and return the response.

        Args:
            request: The EsiRequest instance to execute.
            session: An aiohttp ClientSession to use for making the HTTP request.

        Returns:
            A tuple containing the original EsiRequest and an EsiResponse instance.

        """
        ...

    async def execute_requests(
        self, requests: EsiRequests
    ) -> tuple[EsiRequests, dict[UUID, EsiResponse]]:
        """Execute a batch of ESI requests and return the responses.

        Args:
            requests: The EsiRequests instance containing the batch of requests to execute.

        Returns:
            A tuple containing the original EsiRequests instance and a dictionary mapping request UUIDs to EsiResponse instances.

        """
        ...
