"""Factory for creating ESI Link objects."""

from pathlib import Path
from typing import Literal

from aiolimiter import AsyncLimiter

from esi_link.cache.diskcache_cache import DiskCache
from esi_link.cache.json_disk_cache import JsonDiskCache
from esi_link.esi_auth.auth_provider import AuthProvider
from esi_link.esi_auth.authenticator import Authenticator
from esi_link.esi_auth.credentials_provider import CredentialsProvider
from esi_link.esi_auth.protocols import AuthProviderProtocol
from esi_link.esi_auth.simple_json_store import CharacterTokenManager
from esi_link.handlers.plugin_manager.response_group_plugin_loader import (
    ResponseGroupHandlerPluginLoader,
)
from esi_link.handlers.plugin_manager.response_plugin_loader import (
    ResponseHandlerPluginLoader,
)
from esi_link.handlers.response.manager import ResponseHandlerManager
from esi_link.handlers.response_group.manager import (
    ResponseGroupHandlerManager,
)
from esi_link.models_and_protocols import (
    CacheManagerProtocol,
    IndexedEsiSchema,
    RequestGroupExecutorProtocol,
    RequestGroupValidatorProtocol,
    RequestValidatorProtocol,
    RuntimeRequestInfoGeneratorProtocol,
)
from esi_link.requests.group_executor import GroupExecutor
from esi_link.requests.request_executor import RequestExecutor
from esi_link.requests.runtime_request_group_info import (
    RuntimeRequestGroupInfoGenerator,
)
from esi_link.requests.runtime_request_info import RuntimeRequestInfoGenerator
from esi_link.validation.request_group_validation import RequestGroupValidator
from esi_link.validation.request_validation import RequestValidator


class EsiLinkObjectFactory:
    def __init__(
        self,
        schema: IndexedEsiSchema,
        cache_directory: Path,
        credentials_file: Path,
        tokens_dir: Path,
        cache_type: Literal["diskcache", "json"] = "json",
        rate_limit_max_rate: float = 10.0,
        rate_limit_time_period: float = 1.0,
        auth_min_seconds: int = 300,
        response_handler_plugins_config: Path | None = None,
        response_group_handler_plugins_config: Path | None = None,
    ) -> None:
        """This factory is used to create ESI Link objects.

        The factory centralizes the creation of all ESI Link components, ensuring that
        they are created with the correct dependencies and configurations.

        Args:
            schema: The IndexedEsiSchema to use for request validation and runtime info generation.
            cache_directory: The directory to use for caching ESI responses.
            credentials_file: The path to the application credentials JSON file for ESI authentication.
            tokens_dir: The directory to use for storing ESI authentication tokens.
            cache_type: The type of cache to use for ESI responses. Can be "diskcache" or "json". Defaults to "json".
            rate_limit_max_rate: The maximum number of requests per time period for ESI rate limiting. Defaults to 10.0.
            rate_limit_time_period: The time period (in seconds) for ESI rate limiting. Defaults to 1.0.
            auth_min_seconds: The minimum number of seconds of validity required for an
                authentication token before it is considered invalid and a new token must
                be obtained. Defaults to 300 seconds (5 minutes).
            response_handler_plugins_config: Optional path to a YAML configuration file for response handler plugins.
            response_group_handler_plugins_config: Optional path to a YAML configuration file for response group handler plugins

        """
        self._schema = schema
        self._auth_min_seconds = auth_min_seconds
        self._max_rate = rate_limit_max_rate
        self._time_period = rate_limit_time_period
        self._credentials_file = credentials_file
        self._tokens_dir = tokens_dir
        self._cache_type = cache_type
        self._cache_directory = cache_directory
        self._response_handler_plugins_config = response_handler_plugins_config
        self._response_group_handler_plugins_config = (
            response_group_handler_plugins_config
        )

    def cache_manager(self) -> CacheManagerProtocol:
        """Get a CacheManagerProtocol instance based on the factory's configuration."""
        if self._cache_type == "diskcache":
            return DiskCache(self._cache_directory)
        elif self._cache_type == "json":
            return JsonDiskCache(self._cache_directory)
        else:
            raise ValueError(f"Unsupported cache type: {self._cache_type}")

    def request_executor(self) -> RequestExecutor:
        """Create a RequestExecutor with the factory's dependencies."""
        return RequestExecutor(
            self.cache_manager(), AsyncLimiter(self._max_rate, self._time_period)
        )

    def runtime_request_gen(self) -> RuntimeRequestInfoGeneratorProtocol:
        """Create a RuntimeRequestInfoGeneratorProtocol with the factory's dependencies."""
        return RuntimeRequestInfoGenerator(
            indexed_schema=self._schema,
            auth=self.auth_provider(),
            auth_min_seconds=self._auth_min_seconds,
            response_handler_manager=self.response_handler_manager(),
        )

    def runtime_group_info_gen(self) -> RuntimeRequestGroupInfoGenerator:
        """Create a RuntimeRequestGroupInfoGenerator with the factory's dependencies."""
        return RuntimeRequestGroupInfoGenerator(
            response_group_handler_manager=self.response_group_handler_manager()
        )

    def group_executor(self) -> RequestGroupExecutorProtocol:
        """Create a RequestGroupExecutorProtocol with the factory's dependencies."""
        return GroupExecutor(
            request_executor=self.request_executor(),
            runtime_request_info=self.runtime_request_gen(),
            runtime_group_info=self.runtime_group_info_gen(),
            request_validator=self.request_validator(),
            request_group_validator=self.request_group_validator(),
        )

    def request_validator(self) -> RequestValidatorProtocol:
        """Create a RequestValidatorProtocol with the factory's dependencies."""
        return RequestValidator(
            schema=self._schema,
            response_handler_manager=self.response_handler_manager(),
            auth_provider=self.auth_provider(),
        )

    def request_group_validator(self) -> RequestGroupValidatorProtocol:
        """Create a RequestGroupValidatorProtocol with the factory's dependencies."""
        return RequestGroupValidator(
            response_group_handler_manager=self.response_group_handler_manager()
        )

    def response_group_handler_manager(self) -> ResponseGroupHandlerManager:
        """Create a ResponseGroupHandlerManager with the factory's dependencies."""
        if self._response_group_handler_plugins_config is not None:
            plugin_loader = ResponseGroupHandlerPluginLoader(
                self._response_group_handler_plugins_config
            )
            manager = ResponseGroupHandlerManager()
            plugin_loader(manager)
            return manager
        return ResponseGroupHandlerManager()

    def response_handler_manager(self) -> ResponseHandlerManager:
        """Create a ResponseHandlerManager with the factory's dependencies."""
        if self._response_handler_plugins_config is not None:
            plugin_loader = ResponseHandlerPluginLoader(
                self._response_handler_plugins_config
            )
            manager = ResponseHandlerManager()
            plugin_loader(manager)
            return manager
        return ResponseHandlerManager()

    def auth_provider(self) -> AuthProviderProtocol:
        """Get the factory's AuthProviderProtocol."""
        credentials_provider = CredentialsProvider(self._credentials_file)
        creds = credentials_provider.get_credentials()
        authenticator = Authenticator(
            client_id=creds.clientId,
            scopes=creds.scopes,
            callback_url=creds.callbackUrl,
        )
        token_manager = CharacterTokenManager(
            self._tokens_dir, authenticator=authenticator
        )
        return AuthProvider(token_manager=token_manager)
