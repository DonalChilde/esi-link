"""ESI Link main module implementation."""

import asyncio
import logging
from copy import deepcopy
from types import CoroutineType
from typing import Any

from esi_auth import CharacterToken, TokenManager
from whenever import Instant

from esi_link import USER_AGENT
from esi_link.helpers import operation_accessors as OA
from esi_link.helpers.build_url import build_url
from esi_link.models import (
    EsiHttpProtocol,
    EsiLinkError,
    EsiLinkProtocol,
    EsiRequest,
    EsiRequests,
    EsiResponse,
    EsiResponses,
    EsiSchema,
    HandlerConfig,
    HandlerManagerProtocol,
    HttpRequest,
    ResponseHandlerProtocol,
)
from esi_link.request_validator import EsiRequestValidatorProtocol

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

APPLICATION_RESPONSE_HANDLERS: list[HandlerConfig] = []

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
        request_validator: EsiRequestValidatorProtocol | None = None,
        application_handlers_config: list[HandlerConfig] | None = None,
    ) -> None:
        """Initialize the EsiLink instance.

        Args:
            esi_schema: The ESI schema to use for building requests.
            esi_http: The ESI HTTP client to use for executing requests.
            handler_manager: The handler manager to use for response handlers.
            token_manager: The token manager to use for authentication.
            application_handlers_config: The application-level response handlers configuration.
        """
        self.esi_schema = esi_schema
        self.esi_http = esi_http
        self.handler_manager = handler_manager
        self.token_manager = token_manager
        self.request_validator = request_validator
        self.application_handlers_config = (
            application_handlers_config
            if application_handlers_config
            else APPLICATION_RESPONSE_HANDLERS
        )

    def _init_handlers(
        self, handler_configs: list[HandlerConfig]
    ) -> list[ResponseHandlerProtocol]:
        """Initialize response handlers."""
        instanced_handlers = [
            self.handler_manager.get_handler(config) for config in handler_configs
        ]
        return instanced_handlers

    async def execute_requests(
        self,
        requests: EsiRequests,
    ) -> EsiResponses:
        """Execute the given EsiRequests asynchronously.

        This method processes a collection of ESI (EVE Swagger Interface) requests by:
        1. Building HTTP requests from the provided EsiRequests
        2. Collecting request coroutines from the HTTP client
        3. Wrapping each response coroutine with a handler
        4. Executing all requests concurrently using asyncio.gather
        5. Returning the responses along with timing information

        Args:
            requests (EsiRequests): A collection of ESI requests to be executed.

        Returns:
            EsiResponses: An object containing:
                - started_at: Timestamp when execution began
                - completed_at: Timestamp when all requests completed
                - responses: A dictionary mapping request IDs to their responses

        Raises:
            Any exceptions raised by the HTTP client or request handlers will propagate
            unless handled by _handler_wrapper.
        """
        started_at = Instant.now()
        async with self.esi_http as http_client:
            http_requests = await self.build_http_requests(requests=requests)
            response_coros = await http_client.collect_request_coros(http_requests)
            request_coros = [self._handler_wrapper(r) for r in response_coros]
            results = await asyncio.gather(*request_coros)
            completed_at = Instant.now()
            return EsiResponses(
                started_at=started_at,
                completed_at=completed_at,
                responses={r.request.request_id: r for r in results},
            )

    def validate_request(self, request: EsiRequest) -> None:
        """Validate the given EsiRequest.

        Args:
            request (EsiRequest): The request to validate.

        Raises:
            ValidationError: If the request is invalid.
        """
        if self.request_validator:
            self.request_validator.validate(request=request)

    # async def collect_request_coros(
    #     self, ctx: ResponseContext, requests: EsiRequests
    # ) -> list[CoroutineType[Any, Any, EsiResponse]]:
    #     """Collect coroutines for the given EsiRequests.

    #     Note: This method returns coroutines that must be executed while the
    #     esi_http context manager is still active. Consider using execute_requests()
    #     instead for proper session lifecycle management.
    #     """
    #     http_requests = self.build_http_requests(ctx=ctx, requests=requests)
    #     async with self.esi_http as http_client:
    #         response_coros = await http_client.collect_request_coros(http_requests)
    #         request_coros = [self._handler_wrapper(ctx, r) for r in response_coros]
    #         return request_coros

    async def _handler_wrapper(
        self,
        response_coro: CoroutineType[Any, Any, EsiResponse],
    ) -> EsiResponse:
        """Wrap the response coroutine to run response handlers."""
        response = await response_coro
        response.metrics.handlers_start = Instant.now()
        app_handlers = self._init_handlers(self.application_handlers_config)
        for handler in app_handlers:
            await handler.handle_response(esi_response=response)
        request_handlers = self._init_handlers(response.request.handlers)
        for handler in request_handlers:
            await handler.handle_response(esi_response=response)
        response.metrics.handlers_end = Instant.now()
        return response

    async def get_auth_tokens_for_requests(
        self,
        esi_requests: EsiRequests,
    ) -> dict[str, dict[int, CharacterToken]]:
        """Get the auth token for the given EsiRequest.

        This method uses the TokenManager to retrieve the appropriate
        CharacterTokens needed by the requests.

        Args:
            esi_requests: The EsiRequests for which to get the auth token.

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
                token_list = await self.token_manager.get_character_tokens(
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
    ) -> dict[str, str | int | float]:
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

    async def build_http_requests(
        self,
        requests: EsiRequests,
    ) -> list[HttpRequest]:
        """Build HttpRequest objects from EsiRequest objects."""
        http_requests: list[HttpRequest] = []
        token_dict = await self.get_auth_tokens_for_requests(esi_requests=requests)
        for req in requests.requests.values():
            url = build_url(req, self.esi_schema)
            indexed_operation = self.esi_schema.operations.get(req.operation_id)
            if not indexed_operation:
                raise EsiLinkError(f"Operation ID not found: {req.operation_id}")
            is_paged = OA.is_paged(indexed_operation)
            http_request_headers = self._collect_http_request_headers(
                esi_request=req, token_dict=token_dict
            )
            http_request = HttpRequest(
                method=indexed_operation.method,
                url=url,
                esi_request=req,
                cache_key=self.esi_http.cache.generate_cache_key(
                    esi_request=req, esi_schema=self.esi_schema
                ),
                headers={
                    key: str(value) for key, value in http_request_headers.items()
                },
                is_paged=is_paged,
                json_body=req.request_body if req.request_body else None,
            )
            http_requests.append(http_request)
        return http_requests


# class LinkManager:
#     """Handles the initialization and management of EsiLink instances."""

#     def __init__(
#         self,
#         esi_schema: dict[str, Any],
#         schema_download_date: Instant,
#         auth_connection_string: str,
#     ) -> None:
#         # FIXME should this be a raw schema or an EsiSchema?
#         self.esi_schema = EsiSchema.from_schema(
#             schema=esi_schema, download_date=schema_download_date
#         )
#         self._handler_manager = self._get_handler_manager()
#         self._token_manager = self._get_token_manager(
#             auth_connection_string=auth_connection_string
#         )

#     def _get_handler_manager(self) -> HandlerManagerProtocol:
#         handler_manager = HandlerManager()
#         # # Register built-in handlers
#         # handler_manager.register_handler(
#         #     JsonFileResponseDataHandler.name, JsonFileResponseDataHandler
#         # )
#         return handler_manager

#     def _get_token_manager(self, auth_connection_string: str) -> TokenManager:
#         token_manager = TokenManager(connection_string=auth_connection_string)
#         return token_manager

#     def esi_link_factory(self) -> EsiLinkProtocol:
#         # TODO allow configuration of cache and HTTP client
#         cache = InMemoryCache()
#         esi_http = EsiHttpRateLimited(cache=cache, esi_schema=self.esi_schema)
#         esi_link = EsiLink(
#             esi_schema=self.esi_schema,
#             esi_http=esi_http,
#             handler_manager=self._handler_manager,
#             token_manager=self._token_manager,
#         )
#         return esi_link
