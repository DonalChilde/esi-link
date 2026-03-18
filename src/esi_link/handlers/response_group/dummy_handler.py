from typing import Self

from esi_link.handlers.response_group.response_group_handlers import logger
from esi_link.models_and_protocols import (
    RequestGroup,
    Response,
    ResponseGroupHandlerConfig,
    ResponseGroupHandlerProtocol,
)


class DummyResponseGroupHandler(ResponseGroupHandlerProtocol):
    """A dummy response group handler that does nothing."""

    name = "esi-link:dummy_group_handler"

    def __init__(self, config: ResponseGroupHandlerConfig) -> None:
        """Initialize the DummyResponseGroupHandler."""
        self.config = config

    async def __call__(
        self, request_group: RequestGroup, responses: list[Response]
    ) -> list[Response]:
        """Handle the responses by doing nothing."""
        logger.info(
            "DummyResponseGroupHandler called for request group %s with %s responses, config: %r",
            request_group.group_id,
            len(responses),
            self.config.model_dump(),
        )
        return responses

    @classmethod
    def from_config(cls, config: ResponseGroupHandlerConfig) -> Self:
        """Create a DummyResponseGroupHandler from a ResponseGroupHandlerConfig."""
        return cls(config=config)

    @classmethod
    def validate_config(cls, config: ResponseGroupHandlerConfig) -> None:
        """Validate the ResponseGroupHandlerConfig for a DummyResponseGroupHandler."""
        pass
