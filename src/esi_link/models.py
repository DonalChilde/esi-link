"""ESI Link Models."""
###########################################################################
# Models
###########################################################################

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import CoroutineType, TracebackType
from typing import Any, Literal, Self
from uuid import UUID

import aiohttp
from pydantic import BaseModel, Field
from whenever import Instant
from yaml import safe_dump, safe_load

from esi_link.helpers.resolve_json_ref import resolve_internal_refs


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


class AuthParams(BaseModel):
    character_id: int
    # client_id: str
    client_alias: str


class EsiRequest(BaseModel):
    """Represents a single ESI request to be executed."""

    request_id: UUID
    operation_id: str
    path_parameters: dict[str, str | int | float] = {}
    query_parameters: dict[str, str | int | float] = {}
    auth_parameters: AuthParams | None = None
    request_body: Any = None
    headers: dict[str, str | int | float] = {}
    handlers: list[HandlerConfig] = []
    """List of handler configurations to apply to this request."""


class EsiRequests(BaseModel):
    """Represents a batch of ESI requests to be executed."""

    created_on: Instant = Field(default_factory=_get_current_instant)
    requests_id: UUID
    description: str = ""
    requests: dict[UUID, EsiRequest]

    def save_to_file(self, file_path: Path, overwrite: bool = False) -> None:
        """Save the EsiRequests instance to a YAML file.

        Args:
            file_path: Path to the file where the YAML representation will be saved.
            overwrite: Whether to overwrite the file if it exists. Defaults to False.
        """
        if file_path.is_dir():
            raise EsiLinkError(f"{file_path} is a directory.")
        if file_path.is_file() and not overwrite:
            raise EsiLinkError(
                f"{file_path} already exists. Use overwrite=True to overwrite."
            )
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as file:
            safe_dump(self.model_dump(mode="json"), file, sort_keys=False)

    @classmethod
    def load_from_file(cls, file_path: Path) -> "EsiRequests":
        """Load an EsiRequests instance from a YAML file.

        Args:
            file_path: Path to the YAML file to load.

        Returns:
            An instance of EsiRequests.
        """
        if not file_path.is_file():
            raise EsiLinkError(f"{file_path} does not exist or is not a file.")
        try:
            data = safe_load(file_path.read_text())
            result = cls.model_validate(data)
        except Exception as e:
            raise EsiLinkError(
                f"Failed to load EsiRequests from {file_path}: {e}"
            ) from e
        return result


class Metrics(BaseModel):
    request_start: Instant | None = None
    request_end: Instant | None = None
    response_start: Instant | None = None
    response_end: Instant | None = None
    handlers_start: Instant | None = None
    handlers_end: Instant | None = None
    pages_required: int | None = None
    pages_fetched: int | None = None
    pages_start: Instant | None = None
    pages_end: Instant | None = None
    cache_check_start: Instant | None = None
    cache_check_end: Instant | None = None
    cache_update_start: Instant | None = None
    cache_update_end: Instant | None = None
    cache_check: Literal["HIT", "MISS", "STALE"] | None = None
    ratelimit_group: str | None = None
    ratelimit_limit: str | None = None
    ratelimit_remaining: str | None = None
    ratelimit_used: str | None = None
    retry_after: str | None = None
    response_source: Literal[
        "CACHE",
        "NETWORK_STALE_CACHE_OK",
        "NETWORK_STALE_CACHE_UPDATED",
        "NETWORK_CACHE_MISS",
        "NETWORK",
        "NOT_SET",
    ] = "NOT_SET"

    def request_duration(self) -> float | None:
        """Calculate the total duration of the request in seconds.

        Returns:
            The total duration in seconds, or None if start or end times are not set.
        """
        if self.request_start and self.response_end:
            delta = self.response_end - self.request_start
            return delta.in_seconds()
        return None

    def response_duration(self) -> float | None:
        """Calculate the duration of the response in seconds.

        Returns:
            The response duration in seconds, or None if start or end times are not set.
        """
        if self.response_start and self.response_end:
            delta = self.response_end - self.response_start
            return delta.in_seconds()
        return None

    def handlers_duration(self) -> float | None:
        """Calculate the duration of the handlers in seconds.

        Returns:
            The handlers duration in seconds, or None if start or end times are not set.
        """
        if self.handlers_start and self.handlers_end:
            delta = self.handlers_end - self.handlers_start
            return delta.in_seconds()
        return None

    def cache_check_duration(self) -> float | None:
        """Calculate the duration of the cache check in seconds.

        Returns:
            The cache check duration in seconds, or None if start or end times are not set.
        """
        if self.cache_check_start and self.cache_check_end:
            delta = self.cache_check_end - self.cache_check_start
            return delta.in_seconds()
        return None

    def cache_update_duration(self) -> float | None:
        """Calculate the duration of the cache update in seconds.

        Returns:
            The cache update duration in seconds, or None if start or end times are not set.
        """
        if self.cache_update_start and self.cache_update_end:
            delta = self.cache_update_end - self.cache_update_start
            return delta.in_seconds()
        return None

    def pages_duration(self) -> float | None:
        """Calculate the duration of the pages fetch in seconds.

        Returns:
            The pages fetch duration in seconds, or None if start or end times are not set.
        """
        if self.pages_start and self.pages_end:
            delta = self.pages_end - self.pages_start
            return delta.in_seconds()
        return None


class ResponseData(BaseModel):
    exceptions: dict[UUID, tuple[EsiRequest, type[BaseException]]] = {}
    metrics: dict[UUID, tuple[EsiRequest, Metrics]] = {}
    http_responses: dict[UUID, tuple[EsiRequest, "HttpResponse"]] = {}


class CachedResponse(BaseModel):
    """Represents a cached ESI response."""

    cache_key: UUID
    """The cache key UUID, built from the EsiRequest."""
    cached_on: Instant = Field(default_factory=_get_current_instant)
    """The instant when the response was cached."""
    response: "HttpResponse"
    """The cached response data."""

    def is_stale(self) -> bool:
        """Determine if the cached response is stale.

        This method should be implemented to check if the cached response is still valid.
        For example, it could check the expiration time or ETag.

        Returns:
            True if the cached response is stale, False otherwise.
        """
        expires_at = self.response.expires_at()
        if expires_at is not None:
            return expires_at < Instant.now()
        return False


@dataclass(slots=True)
class IndexedOperation:
    operation_id: str
    method: str
    path: str
    operation: dict[str, Any] = field(default_factory=dict[str, Any])


class EsiSchema(BaseModel):
    """Represents the ESI OpenAPI schema.

    The schema is normalized and indexed by operation ID for efficient access.
    """

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
        """String representation of the EsiSchema instance."""
        return (
            f"EsiSchema(openapi={self.openapi}, operations={len(self.operations)}, "
            f"download_date={self.download_date})"
        )

    @classmethod
    def from_schema(cls, schema: dict[str, Any], download_date: Instant) -> "EsiSchema":
        """Create an EsiSchema instance from a raw OpenAPI schema dictionary.

        Normalizes and indexes the schema for efficient access.

        Args:
            schema: The OpenAPI schema as a dictionary.
            download_date: The date the schema was downloaded.

        Returns:
            An instance of EsiSchema.
        """
        schema_copy = deepcopy(schema)
        dereferenced_schema = resolve_internal_refs(schema_copy, schema_copy)

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

    def save_to_file(self, file_path: Path, overwrite: bool = False) -> None:
        """Save the EsiSchema instance to a JSON file.

        Args:
            file_path: Path to the file where the JSON representation will be saved.
            overwrite: Whether to overwrite the file if it exists. Defaults to False.
        """
        if file_path.is_dir():
            raise EsiLinkError(
                f"Error trying to save EsiSchema to {file_path}: its a directory."
            )
        if file_path.is_file() and not overwrite:
            raise EsiLinkError(
                f"Error trying to save EsiSchema to {file_path}: File already exists. Use overwrite=True to overwrite."
            )
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as file:
            file.write(self.model_dump_json(indent=2))

    @classmethod
    def load_from_file(cls, file_path: Path) -> "EsiSchema":
        """Load an EsiSchema instance from a JSON file.

        Args:
            file_path: Path to the JSON file to load.

        Returns:
            An instance of EsiSchema.
        """
        with open(file_path) as file:
            esi_schema = cls.model_validate_json(file.read())
        return esi_schema


@dataclass(slots=True)
class HttpRequest:
    method: str
    url: str
    is_paged: bool
    esi_request: EsiRequest
    cache_key: UUID | None = None
    """The cache key UUID, built from the EsiRequest. None if caching is not used."""
    headers: dict[str, str] = field(default_factory=dict[str, str])
    """App level headers to include in the request. These are merged with any request level headers."""
    json_body: Any = None
    """The JSON body for POST/PUT requests."""
    timeout: int = 10
    page_number: int = 0
    """The page number for paged requests."""


class HttpResponse(BaseModel):
    status_code: int
    reason: str | None
    url: str
    headers: tuple[tuple[str, str | None], ...]
    json_data: Any = None
    etag: str = ""
    last_modified: str = ""
    expires: str = ""
    completed_on: Instant = Field(default_factory=_get_current_instant)

    def expires_at(self) -> Instant | None:
        """Get the expiration instant from the Expires header, if present.

        Returns:
            The Instant when the response expires, or None if not present.
        """
        if self.expires:
            try:
                return Instant.parse_rfc2822(self.expires)
            except Exception:
                return None
        return None

    def expires_in(self) -> float | None:
        """Get the number of seconds until the response expires.

        Returns:
            The number of seconds until expiration, or None if not present.
        """
        expires_at = self.expires_at()
        if expires_at is not None:
            delta = expires_at - Instant.now()
            return delta.in_seconds()
        return None

    def has_cache_info(self) -> bool:
        """Check if the response has caching information.

        Returns:
            True if the response has ETag or Expires headers, False otherwise.
        """
        return bool(self.etag and self.expires)

    @classmethod
    def load_config(cls, file_path: Path) -> Self:
        """Load the EsiLinkConfig from a JSON file.

        Args:
            file_path: Path to the JSON configuration file.
        """
        if not file_path.is_file():
            raise EsiLinkError(f"{file_path} does not exist or is not a file.")
        try:
            data = file_path.read_text()
            loaded_config = cls.model_validate_json(data)
            return loaded_config
        except Exception as e:
            raise EsiLinkError(
                f"Failed to load EsiLinkConfig from {file_path}: {e}"
            ) from e

    def save_config(self, file_path: Path, overwrite: bool = False) -> None:
        """Save the EsiLinkConfig to a JSON file.

        Args:
            file_path: Path to the JSON configuration file.
            overwrite: Whether to overwrite the file if it exists. Defaults to False.
        """
        if file_path.is_dir():
            raise EsiLinkError(f"{file_path} is a directory.")
        if file_path.is_file() and not overwrite:
            raise EsiLinkError(
                f"{file_path} already exists. Use overwrite=True to overwrite."
            )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = self.model_dump_json(indent=2)
            with open(file_path, "w") as file:
                file.write(data)
        except Exception as e:
            raise EsiLinkError(
                f"Failed to save EsiLinkConfig to {file_path}: {e}"
            ) from e

    def update_schema(self, schema: dict[str, Any], download_date: Instant) -> None:
        """Update the ESI schema in the configuration.

        Args:
            schema: The new OpenAPI schema as a dictionary.
            download_date: The date the schema was downloaded.
        """
        self.esi_schema = EsiSchema.from_schema(
            schema=schema, download_date=download_date
        )


class EsiResponse(BaseModel):
    """Represents the response for a single ESI request."""

    request: EsiRequest
    http_response: HttpResponse | None
    metrics: Metrics
    error_messages: list[str] = []


class EsiResponses(BaseModel):
    """Represents a batch of ESI responses."""

    started_at: Instant | None = None
    completed_at: Instant | None = None
    responses: dict[UUID, EsiResponse]
    """responses keyed by EsiRequest.request_id"""


############################################################################
# Protocols
############################################################################
class ResponseHandlerProtocol:
    """Protocol for handling ESI responses."""

    name: str

    async def handle_response(
        self,
        esi_response: EsiResponse,
    ) -> Any:
        """Handle the response from an ESI request.

        Args:
            ctx: The response context.
            esi_response: The EsiResponse object.

        Returns:
            The processed response data.
        """
        ...

    @classmethod
    def from_config(cls, config: HandlerConfig) -> "ResponseHandlerProtocol":
        """Create an instance of the handler from a configuration.

        Args:
            config: The HandlerConfig instance containing the configuration.

        Returns:
            An instance of the handler.

        Raises:
            InvalidHandlerError: If the handler cannot be instantiated.
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


class CacheProtocol:
    def generate_cache_key(
        self, esi_request: EsiRequest, esi_schema: EsiSchema
    ) -> UUID | None:
        """Generate a cache key for the given ESI request.

        Args:
            esi_request: The EsiRequest instance for which to generate the cache key.
            esi_schema: The EsiSchema instance representing the ESI OpenAPI schema.

        Returns:
            A UUID representing the cache key, or None if caching is not applicable.

        ...
        """
        ...

    def is_cached(self, cache_key: UUID) -> bool:
        """Check if a response is cached for the given cache key.

        Args:
            cache_key: The UUID cache key to check.

        Returns:
            True if a cached response exists for the cache key, False otherwise.
        ...
        """
        ...

    def get_cached_response(self, cache_key: UUID) -> CachedResponse | None:
        """Retrieve a cached response by its cache key.

        Args:
            cache_key: The UUID cache key of the cached response.

        Returns:
            The CachedResponse instance if found, otherwise None.

        ...
        """
        ...

    def store_http_response(self, cache_key: UUID, http_response: HttpResponse) -> None:
        """Store an http response.

        Args:
            cache_key: The UUID cache key for the cached response.
            http_response: The HttpResponse instance to cache.

        ...
        """
        ...

    def update_http_response(
        self, cache_key: UUID, http_response: HttpResponse
    ) -> None:
        """Update an existing cached http response.

        Args:
            cache_key: The UUID cache key for the cached response.
            http_response: The HttpResponse instance to update in the cache.

        ...
        """
        ...


class EsiLinkProtocol:
    """Protocol for ESI Link implementations."""

    esi_schema: EsiSchema
    """The ESI OpenAPI schema."""
    esi_http: "EsiHttpProtocol"
    """The ESI HTTP client implementation."""
    handler_manager: HandlerManagerProtocol
    """The handler manager for response handlers."""

    async def execute_requests(
        self,
        requests: EsiRequests,
    ) -> EsiResponses:
        """Execute a batch of ESI requests.

        Args:
            ctx: The ResponseContext instance.
            requests: The EsiRequests instance containing the requests to execute.

        Returns:
            An EsiResponses instance containing the responses.
        """
        ...

    def validate_request(
        self,
        request: EsiRequest,
    ) -> None:
        """Validate the given ESI request.

        Args:
            request (EsiRequest): The request to validate.

        Raises:
            ValidationError: If the request is invalid.
        """
        ...


class EsiHttpProtocol:
    """Protocol for ESI HTTP client implementations."""

    session: aiohttp.ClientSession | None
    cache: CacheProtocol
    esi_schema: EsiSchema

    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager."""
        ...

    async def execute_requests(
        self,
        requests: list[HttpRequest],
    ) -> list[EsiResponse]:
        """Execute a list of HTTP requests.

        Args:
            requests: A list of HttpRequest instances to execute.

        Returns:
            A list of tuples containing the HttpRequest and either None or an exception if one occurred.
        """
        ...

    async def collect_request_coros(
        self,
        requests: list[HttpRequest],
    ) -> list[CoroutineType[Any, Any, EsiResponse]]:
        """Collect coroutines for executing HTTP requests.

        Args:
            requests: A list of HttpRequest instances to execute.

        Returns:
            A list of coroutines for executing the requests.
        """
        ...


##################################################################################
# Exceptions
##################################################################################


class EsiLinkError(Exception):
    """Base exception for ESI Link errors."""

    pass


class HandlerConfigError(EsiLinkError):
    """Raised when there is an error in handler configuration."""

    def __init__(self, message: str, handler_config: HandlerConfig) -> None:
        """Initialize the HandlerConfigError."""
        super().__init__(message)
        self.handler_config = handler_config

    pass


class ResponseHandlerError(EsiLinkError):
    """Raised when a response handler encounters an error."""

    def __init__(
        self, message: str, handler_name: str, response: EsiResponse | None
    ) -> None:
        """Initialize the ResponseHandlerError."""
        super().__init__(message)
        self.handler_name = handler_name
        self.response = response

    pass


class InvalidHandlerError(ResponseHandlerError):
    """Raised when a handler is invalid or cannot be instantiated."""

    pass
