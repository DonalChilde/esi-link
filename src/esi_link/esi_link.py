import logging
from typing import Any

from whenever import Instant

from esi_link import operation_accessors as OA
from esi_link.build_url import build_url
from esi_link.cache_p import InMemoryCache
from esi_link.esi_http import EsiHttpRateLimited
from esi_link.models import (
    EsiHttpProtocol,
    EsiLinkError,
    EsiLinkProtocol,
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
        # Register built-in handlers
        handler_manager.register_handler(
            JsonFileResponseHandler.name, JsonFileResponseHandler
        )
        return handler_manager

    def esi_link_factory(self) -> EsiLinkProtocol:
        # TODO allow configuration of cache and HTTP client
        cache = InMemoryCache()
        esi_http = EsiHttpRateLimited(cache=cache, esi_schema=self.esi_schema)
        esi_link = EsiLink(
            esi_schema=self.esi_schema,
            esi_http=esi_http,
            handler_manager=self._handler_manager,
        )
        return esi_link
