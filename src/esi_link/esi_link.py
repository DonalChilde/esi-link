import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from esi_auth import CharacterToken, TokenManager
from whenever import Instant

from esi_link import operation_accessors as OA
from esi_link.build_url import build_url
from esi_link.cache_p import InMemoryCache
from esi_link.esi_http import EsiHttpRateLimited
from esi_link.models import (
    EsiHttpProtocol,
    EsiLinkError,
    EsiLinkProtocol,
    EsiRequest,
    EsiRequests,
    EsiSchema,
    HandlerConfig,
    HandlerManagerProtocol,
    HttpRequest,
    ResponseContext,
    ResponseHandlerProtocol,
)
from esi_link.response_handlers import HandlerManager, JsonFileResponseHandler

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
USER_AGENT = "esi-link/0.1.0"

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
        token_manager: TokenManager | None = None,
        application_handlers_config: list[HandlerConfig] | None = None,
    ) -> None:
        self.esi_schema = esi_schema
        self.esi_http = esi_http
        self.handler_manager = handler_manager
        self.token_manager = token_manager
        self.application_handlers_config = (
            application_handlers_config if application_handlers_config else []
        )
        self.app_handlers: list[ResponseHandlerProtocol] = self._init_handlers(
            self.application_handlers_config
        )

    def _init_handlers(
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
        """Execute the given EsiRequests asynchronously."""
        http_requests = self.build_http_requests(ctx=ctx, requests=requests)
        async with self.esi_http as http_client:
            await http_client.execute_requests(http_requests)
        return None

    def get_auth_tokens_for_requests(
        self,
        esi_requests: EsiRequests,
    ) -> dict[str, dict[int, CharacterToken]]:
        """Get the auth token for the given EsiRequest.

        This method uses the TokenManager to retrieve the appropriate
        CharacterTokens needed by the requests.

        Args:
            esi_request: The EsiRequest for which to get the auth token.

        Returns:
            The CharacterToken if found, otherwise None.
        Raises:
            EsiLinkError: If no TokenManager is configured or if the token
                cannot be found.
        """
        token_dict: dict[str, dict[int, CharacterToken]] = {}
        needs_token = [x for x in esi_requests.requests.values() if x.auth_parameters]
        if needs_token and not self.token_manager:
            raise EsiLinkError(
                "EsiRequest requires auth tokens but no TokenManager is configured."
            )
        if not needs_token:
            return token_dict
        for needy in needs_token:
            auth_params = needy.auth_parameters
            if not auth_params:
                continue
            client_alias = auth_params.client_alias
            character_id = auth_params.character_id
            if client_alias not in token_dict:
                assert self.token_manager is not None, (
                    "TokenManager should never be None here."
                )
                token_list = self.token_manager.get_character_tokens(
                    credential_alias=client_alias, buffer=5
                )
                token_dict[client_alias] = {
                    token.character_id: token for token in token_list
                }
            if character_id not in token_dict[client_alias]:
                raise EsiLinkError(
                    f"No token found for client_alias={client_alias} "
                    f"and character_id={character_id}"
                )
        return token_dict

    def _collect_http_request_headers(
        self, esi_request: EsiRequest, token_dict: dict[str, dict[int, CharacterToken]]
    ) -> dict[str, str]:
        """Collect HTTP request headers for the given EsiRequest."""
        http_request_headers = deepcopy(esi_request.headers)
        # Add Authorization header if needed
        auth_params = esi_request.auth_parameters
        if auth_params:
            client_alias = auth_params.client_alias
            character_id = auth_params.character_id
            character_tokens = token_dict.get(client_alias, {})
            token = character_tokens.get(character_id)
            if not token:
                raise EsiLinkError(
                    f"No token found for client_alias={client_alias} "
                    f"and character_id={character_id}"
                )
            http_request_headers["Authorization"] = f"Bearer {token.access_token}"
            http_request_headers["User-Agent"] = USER_AGENT
        return http_request_headers

    def build_http_requests(
        self,
        ctx: ResponseContext,
        requests: EsiRequests,
    ) -> list[HttpRequest]:
        """Build HttpRequest objects from EsiRequest objects."""
        http_requests: list[HttpRequest] = []
        token_dict = self.get_auth_tokens_for_requests(esi_requests=requests)
        for req in requests.requests.values():
            url = build_url(req, self.esi_schema)
            indexed_operation = self.esi_schema.operations.get(req.operation_id)
            if not indexed_operation:
                raise EsiLinkError(f"Operation ID not found: {req.operation_id}")
            user_handlers = self._init_handlers(req.handlers)
            is_paged = OA.is_paged(indexed_operation)
            http_request_headers = self._collect_http_request_headers(
                esi_request=req, token_dict=token_dict
            )
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
                headers=http_request_headers,
                is_paged=is_paged,
            )
            http_requests.append(http_request)
        return http_requests


class LinkManager:
    """Handles the initialization and management of EsiLink instances."""

    def __init__(
        self,
        esi_schema: dict[str, Any],
        schema_download_date: Instant,
        token_file_path: Path | None = None,
    ) -> None:
        self.esi_schema = EsiSchema.from_schema(
            schema=esi_schema, download_date=schema_download_date
        )
        self._handler_manager = self._get_handler_manager()
        self._token_manager = self._get_token_manager(token_file_path=token_file_path)

    def _get_handler_manager(self) -> HandlerManagerProtocol:
        handler_manager = HandlerManager()
        # Register built-in handlers
        handler_manager.register_handler(
            JsonFileResponseHandler.name, JsonFileResponseHandler
        )
        return handler_manager

    def _get_token_manager(
        self, token_file_path: Path | None = None
    ) -> TokenManager | None:
        if token_file_path is None:
            return None
        token_manager = TokenManager(store_path=token_file_path)
        return token_manager

    def esi_link_factory(self) -> EsiLinkProtocol:
        # TODO allow configuration of cache and HTTP client
        cache = InMemoryCache()
        esi_http = EsiHttpRateLimited(cache=cache, esi_schema=self.esi_schema)
        esi_link = EsiLink(
            esi_schema=self.esi_schema,
            esi_http=esi_http,
            handler_manager=self._handler_manager,
            token_manager=self._token_manager,
        )
        return esi_link
