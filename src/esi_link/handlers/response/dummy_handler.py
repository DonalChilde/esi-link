import logging
from typing import Self

from esi_link.models_and_protocols import (
    Response,
    ResponseHandlerConfig,
    ResponseHandlerProtocol,
)

logger = logging.getLogger(__name__)


class DummyResponseHandler(ResponseHandlerProtocol):
    """A dummy response handler that does nothing."""

    name = "esi-link:dummy"

    def __init__(self, config: ResponseHandlerConfig) -> None:
        """Initialize the DummyResponseHandler."""
        self.config = config

    async def __call__(self, response: Response) -> Response:
        """Handle the response by doing nothing."""
        if response.http_response is None:
            logger.info(
                "DummyResponseHandler called with response with no http_response, name: %s, config: %r",
                response.request.request_id,
                self.config.model_dump(),
            )
            return response
        logger.info(
            "DummyResponseHandler called with config: %r, for url: %s",
            self.config.model_dump(),
            response.http_response.url,
        )
        return response

    @classmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        """Create a DummyResponseHandler from a HandlerConfig."""
        return cls(config=config)

    @classmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        """Validate the HandlerConfig for a DummyResponseHandler."""
        pass
