"""These are dummy implementations of the various protocols used in the request execution process.

They can be used for testing or as placeholders until real implementations are provided.
"""

import logging
from typing import Self

from esi_link.models_and_protocols import (
    Request,
    RequestGroup,
    RequestGroupValidatorProtocol,
    RequestValidatorProtocol,
    Response,
    ResponseHandlerConfig,
    ResponseHandlerManagerProtocol,
    ResponseHandlerProtocol,
)

logger = logging.getLogger(__name__)


class DummyRequestValidator(RequestValidatorProtocol):
    async def __call__(self, request: Request) -> None:
        pass


class DummyRequestGroupValidator(RequestGroupValidatorProtocol):
    def __call__(self, request_group: RequestGroup) -> None:
        pass


class DummyResponseHandler(ResponseHandlerProtocol):
    name = "esi-link:dummy"

    def __init__(self, config: ResponseHandlerConfig) -> None:

        self.config = config

    async def __call__(self, response: Response) -> Response:
        if response.http_response is None:
            logger.info(
                "DummyResponseHandler called with response with no http_response, name: %s, config: %s",
                self.config,
            )
            return response
        logger.info(
            "DummyResponseHandler called with config: %s, for url: %s",
            self.config,
            response.http_response.url,
        )
        return response

    @classmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        return cls(config=config)

    @classmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        pass


class DummyResponseHandlerManager(ResponseHandlerManagerProtocol):
    def get_handler(
        self, config: ResponseHandlerConfig
    ) -> ResponseHandlerProtocol | None:
        return DummyResponseHandler(config=config)

    def register_handler(self, handler_cls: type[ResponseHandlerProtocol]) -> None:
        return None

    def registered_handlers(self) -> dict[str, type[ResponseHandlerProtocol]]:
        return {}

    def validate_handler_config(self, config: ResponseHandlerConfig) -> None:
        pass
