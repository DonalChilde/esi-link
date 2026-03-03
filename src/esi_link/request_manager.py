"""Top level class for running ESI requests."""

import asyncio
import logging
from time import perf_counter

from esi_link.auth_provider import DummyAuthProvider
from esi_link.esi_schema import load_schema_store
from esi_link.handler_manager import DummyHandlerManager
from esi_link.json_disk_cache import JsonDiskCache
from esi_link.models import (
    CacheManagerProtocol,
    EsiLinkException,
    EsiRequest,
    EsiRequestExecutionManagerProtocol,
    EsiResponse,
    EsiRuntimeRequest,
    HandlerManagerProtocol,
    IndexedEsiSchema,
    RequestValidatorProtocol,
    UrlGeneratorProtocol,
)
from esi_link.request_executor import EsiRequestExecutor
from esi_link.request_validation import RequestValidator
from esi_link.runtime_request_generator import RuntimeRequestGenerator
from esi_link.settings import EsiLinkSettings, get_settings
from esi_link.url_generator import UrlGenerator

logger = logging.getLogger(__name__)


class EsiLink(EsiRequestExecutionManagerProtocol):
    def __init__(
        self,
        *,
        settings: EsiLinkSettings | None = None,
        schema: IndexedEsiSchema | None = None,
        handler_manager: HandlerManagerProtocol | None = None,
        validator: RequestValidatorProtocol | None = None,
        url_generator: UrlGeneratorProtocol | None = None,
        # runtime_info_generator: RuntimeInfoGeneratorProtocol | None = None,
        language: str = "en",
    ) -> None:
        """Initialize the EsiLink instance."""
        self.settings = settings or get_settings()
        self.schema = schema or load_schema_store().latest_schema()
        if not self.schema:
            raise EsiLinkException(
                "The schema store is empty, download a schema and try again."
            )
        self.auth_provider = DummyAuthProvider()
        self.handler_manager = handler_manager or DummyHandlerManager()
        self.cache = self._init_cache()
        self.handler_manager: HandlerManagerProtocol
        self.validator = validator or RequestValidator(
            schema=self.schema, handler_manager=self.handler_manager
        )
        self.url_generator = url_generator or UrlGenerator(schema=self.schema)
        self.language = language

    def validate(self, request: EsiRequest) -> None:
        """Validate the request against the schema.

        Raises:
            ValidationError: If the request is invalid.
        """
        self.validator.validate(request)

    def _make_esi_runtime_request(self, request: EsiRequest) -> EsiRuntimeRequest:
        """Convert an EsiRequest to an EsiRuntimeRequest by populating the runtime info."""
        if self.schema is None:
            raise EsiLinkException("Schema must be loaded to set runtime info")
        runtime_info_generator = RuntimeRequestGenerator(
            operation=self.schema.operations[request.operation_id],
            compatibility_date=self.schema.version,
            auth_provider=self.auth_provider,
            url_generator=self.url_generator,
            language=self.language,
        )
        return runtime_info_generator.get_runtime_request(request)

    # def _get_runtime_info(self, request: EsiRequest) -> RuntimeRequestInfo:
    #     """Get runtime information for the request."""
    #     if self.schema is None:
    #         raise EsiLinkException("Schema must be loaded to set runtime info")
    #     runtime_info_generator = RuntimeInfoGenerator(
    #         operation=self.schema.operations[request.operation_id],
    #         compatibility_date=self.schema.version,
    #         auth_provider=self.auth_provider,
    #         url_generator=self.url_generator,
    #         language=self.language,
    #     )
    #     request_info = runtime_info_generator.generate_runtime_info(request)
    #     return request_info

    async def _handle_response(self, response: EsiResponse) -> EsiResponse:
        """Handle the response."""
        for handler_config in response.request.response_handlers:
            try:
                await self.handler_manager.get_handler(handler_config).handle_response(
                    response
                )
            except Exception as e:
                logger.error(
                    f"Error handling response to request {response.request.request_id} with handler {handler_config}: {e}"
                )
                response.exceptions.append(e)
                response.exception_messages.append(str(e))

        return response

    async def handle_responses(self, responses: list[EsiResponse]) -> list[EsiResponse]:
        """Handle a list of responses."""
        logger.info(
            f"Handling {len(responses)} responses. Responses with handlers = "
            f"{sum(1 for r in responses if r.request.response_handlers)} Total Handlers = "
            f"{sum(len(r.request.response_handlers) for r in responses)}."
        )
        start = perf_counter()
        for response in responses:
            await self._handle_response(response)
        logger.info(
            f"Finished handling responses in {perf_counter() - start:.4f} seconds."
        )
        return responses

    async def send_runtime_requests(
        self,
        requests: list[EsiRuntimeRequest],
        *,
        max_rate: int,
        period: float,
        timeout: float,
    ) -> list[EsiResponse]:
        """Send the requests and return the responses."""
        executor = EsiRequestExecutor(
            cache_manager=self.cache,
            max_rate=max_rate,
            period=period,
            # timeout=timeout,
        )
        logger.info(
            f"Executing {len(requests)} requests with max_rate={max_rate}, period={period}, timeout={timeout}"
        )
        start = perf_counter()
        responses = await executor.execute_requests(requests=requests)
        logger.info(
            f"Received {len(responses)} responses in {perf_counter() - start:.4f} seconds."
        )
        self.log_response_metrics(responses)
        return responses

    def log_response_metrics(self, responses: list[EsiResponse]) -> None:
        """Log metrics about the responses."""
        # TODO use metrics to log:
        # - cache hit/miss rates
        # - 304 vs 200 rates
        # - exception rates
        ...

    def execute_requests(
        self,
        requests: list[EsiRequest],
        *,
        max_rate: int = 100,
        period: float = 60.0,
        timeout: float = 10.0,
    ) -> list[EsiResponse]:
        """Execute the requests and run the response handlers, then return the responses."""
        runtime_requests: list[EsiRuntimeRequest] = []
        for request in requests:
            self.validate(request)
            runtime_requests.append(self._make_esi_runtime_request(request))
        responses = asyncio.run(
            self.send_runtime_requests(
                runtime_requests, max_rate=max_rate, period=period, timeout=timeout
            )
        )
        responses = asyncio.run(self.handle_responses(responses))
        return responses

    def _init_cache(self) -> CacheManagerProtocol:
        """Initialize the cache manager."""
        return JsonDiskCache(cache_directory=self.settings.json_cache_directory)
