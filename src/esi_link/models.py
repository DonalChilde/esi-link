###########################################################################
# Models
###########################################################################

# TODO make utility commands in cli to output UUID and Instant in iso format to support hand crafting Esi Requests.


from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any, Optional, Self, Type, TypedDict
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
    auth_parameters: Optional[AuthParams] = None
    request_body: Any = None
    headers: dict[str, str] = {}
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


class Metrics(TypedDict):
    request_start: Instant
    request_end: Instant
    response_start: Instant
    response_end: Instant
    handlers_start: Instant
    handlers_end: Instant
    pages_fetched: int
    pages_start: Instant
    pages_end: Instant
    ratelimit_group: str
    ratelimit_limit: str
    ratelimit_remaining: int
    ratelimit_used: int
    ratelimit_retry_after: float


class ResponseData(BaseModel):
    exceptions: dict[UUID, tuple[EsiRequest, Type[BaseException]]] = {}
    metrics: dict[UUID, tuple[EsiRequest, Metrics]] = {}
    http_responses: dict[UUID, tuple[EsiRequest, "HttpResponse"]] = {}


class ResponseContext(BaseModel):
    obj: dict[str, Any] = {}
    response_data: ResponseData = Field(default_factory=ResponseData)


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
        # Placeholder implementation; actual logic will depend on caching strategy.
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


@dataclass(slots=True)
class HttpRequest:
    method: str
    url: str
    is_paged: bool
    ctx: ResponseContext
    esi_request: EsiRequest
    cache_key: Optional[UUID] = None
    """The cache key UUID, built from the EsiRequest. None if caching is not used."""
    app_handlers: list["ResponseHandlerProtocol"] = field(
        default_factory=list["ResponseHandlerProtocol"]
    )
    """App level handlers to process the response. These are run before any request level handlers."""
    user_handlers: list["ResponseHandlerProtocol"] = field(
        default_factory=list["ResponseHandlerProtocol"]
    )
    """Request level handlers to process the response. These are run after any app level handlers."""
    headers: dict[str, str] = field(default_factory=dict[str, str])
    """App level headers to include in the request. These are merged with any request level headers."""
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


class EsiLinkConfig(BaseModel):
    """Application data for Esi Link."""

    esi_schema_url: str = "https://esi.evetech.net/meta/openapi.json"
    """URL to download the ESI OpenAPI schema."""
    esi_schema: EsiSchema | None = None
    """The ESI OpenAPI schema."""
    application_response_handlers: list[HandlerConfig] = []
    """List of application level response handler configurations."""
    cache_connection_string: str = "esi-link-memory://"
    """Connection string for the cache backend.

    Format: [cache_type]://[path_or_connection_info]

    Examples:
        File-based cache: esi-link-json:///path/to/cache/dir
        In-memory cache: esi-link-memory://"""
    connection_max_rate: int = 100
    """Maximum number of concurrent connections per period to ESI."""
    connection_period: float = 60.0
    """Time period in seconds for the maximum connection rate."""
    esi_auth_connection_string: str | None = None
    """Connection string for the ESI authentication store.

    #TODO support multiple auth store types. For now use JSON file store.
    Format: [auth_store_type]://[path_or_connection_info]

    Examples:
        JSON file store: esi-link-auth-json:///path/to/auth_store.json
    """

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


############################################################################
# Protocols
############################################################################
class ResponseHandlerProtocol:
    """Protocol for handling ESI responses."""

    name: str

    async def handle_response(
        self,
        ctx: ResponseContext,
        http_response: HttpResponse,
        request: EsiRequest,
    ) -> Any:
        """Handle the response from an ESI request.

        Args:
            ctx: The response context.
            http_response: The HttpResponse object.
            request: The original EsiRequest object.

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
            request: The EsiRequest instance for which to generate the cache key.
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

    def get_cached_response(self, cache_key: UUID) -> Optional[CachedResponse]:
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
        ctx: ResponseContext,
        requests: EsiRequests,
    ) -> list[tuple[HttpRequest, BaseException | None]]:
        """Execute a batch of ESI requests.

        Args:
            requests: The EsiRequests instance containing the requests to execute.
            session: An optional aiohttp ClientSession to use for the requests.
            response_handler: An optional ResponseHandlerProtocol to process responses.

        Returns:
            A list of tuples containing the HttpRequest and either None or an exception if one occurred.
        """
        ...


class EsiHttpProtocol:
    """Protocol for ESI HTTP client implementations."""

    session: aiohttp.ClientSession | None
    cache: CacheProtocol
    esi_schema: EsiSchema

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def execute_requests(
        self,
        requests: list[HttpRequest],
    ) -> list[tuple[HttpRequest, None | BaseException]]:
        """Execute a list of HTTP requests.

        Args:
            requests: A list of HttpRequest instances to execute.

        Returns:
            A list of tuples containing the HttpRequest and either None or an exception if one occurred.
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
        super().__init__(message)
        self.handler_config = handler_config

    pass


class ResponseHandlerError(EsiLinkError):
    """Raised when a response handler encounters an error."""

    def __init__(
        self, message: str, handler_name: str, response: HttpResponse | None
    ) -> None:
        super().__init__(message)
        self.handler_name = handler_name
        self.response = response

    pass


class InvalidHandlerError(ResponseHandlerError):
    """Raised when a handler is invalid or cannot be instantiated."""

    pass
