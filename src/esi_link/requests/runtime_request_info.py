"""Module for generating runtime request information from ESI requests."""

from esi_link import USER_AGENT
from esi_link.esi_auth.auth_store import AuthStoreDisk

# from esi_link.handlers.response.manager import ResponseHandlerManager
from esi_link.models_and_protocols import (
    EsiSchema,
    Request,
    RequestMetrics,
    # ResponseHandlerManagerProtocol,
    # ResponseHandlerProtocol,
    RuntimeRequestInfo,
    RuntimeRequestInfoGeneratorProtocol,
    UrlGeneratorProtocol,
)
from esi_link.requests.url_generator import UrlGenerator


class RuntimeRequestInfoGenerator(RuntimeRequestInfoGeneratorProtocol):
    def __init__(
        self,
        schema: EsiSchema,
        auth_store: AuthStoreDisk,
        auth_min_seconds: int = 300,
        url_generator: UrlGeneratorProtocol | None = None,
        # response_handler_manager: ResponseHandlerManagerProtocol | None = None,
    ) -> None:
        """Initialize the RuntimeRequestInfoGenerator."""
        self.schema = schema
        self.auth_store = auth_store
        self.auth_min_seconds = auth_min_seconds

        self.url_generator = url_generator or UrlGenerator()
        # self.response_handler_manager = (
        #     response_handler_manager or ResponseHandlerManager()
        # )

    async def __call__(self, request: Request) -> RuntimeRequestInfo:
        """Generate the RuntimeRequestInfo for a given Request."""
        url_info = self.url_generator(request, self.schema)
        headers = self._generate_headers(request)
        auth_headers = await self._auth_headers(request)
        headers.update(auth_headers)
        operation = self.schema.operations.get(request.operation_id)
        if operation is None:
            raise ValueError(
                f"Operation with ID {request.operation_id} not found in indexed schema for request {request.request_id}."
            )

        # handlers: list[ResponseHandlerProtocol] = []
        # for handler_config in request.response_handlers:
        #     handler = self.response_handler_manager.get_handler(handler_config)
        #     if handler is None:
        #         raise ValueError(
        #             f"Response handler with ID {handler_config.name} not found for request {request.request_id}."
        #         )
        #     handlers.append(handler)

        runtime_info = RuntimeRequestInfo(
            path_url=url_info.path_url,
            additional_query_params={},
            method=operation.method,
            is_paged=operation.is_paged,
            is_auth=operation.auth_required,
            headers=headers,
            timeout=10,
            cache_key=url_info.cache_key if operation and operation.is_cached else None,
            # response_handlers=handlers,
            metrics=RequestMetrics(),
        )
        return runtime_info

    async def _auth_headers(self, request: Request) -> dict[str, str]:
        if request.auth_character_id is None:
            return {}
        try:
            char_auth = await self.auth.character_auth(
                request.auth_character_id, min_seconds=self.auth_min_seconds
            )
        except KeyError as e:
            raise ValueError(
                f"Authentication required for character ID {request.auth_character_id}, "
                "but no authentication information is available."
            ) from e
        auth_headers = char_auth.auth_headers
        return auth_headers

    def _generate_headers(self, request: Request) -> dict[str, str]:
        headers: dict[str, str] = {}
        headers["User-Agent"] = USER_AGENT
        headers["Accept-Language"] = request.lang
        headers["X-Compatibility-Date"] = self.schema.compatibility_date
        return headers
