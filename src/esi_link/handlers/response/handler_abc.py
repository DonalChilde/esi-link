"""Abstract base class for response handlers."""

from typing import Self

from esi_link.models_and_protocols import (
    Response,
    ResponseHandlerConfig,
    ResponseHandlerProtocol,
)


class ResponseHandlerABC(ResponseHandlerProtocol):
    """Abstract base class for response handlers.

    This class defines the interface for response handlers, and provides some common
    functionality. Subclasses must implement the `__call__` method to handle the
    response.
    """

    name = "esi-link:response_handler_abc"

    def __init__(self, config: ResponseHandlerConfig) -> None:
        self.config = config

    async def __call__(self, response: Response) -> Response:
        """Handle the response."""
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        """Create a response handler from a ResponseHandlerConfig."""
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        """Validate the ResponseHandlerConfig for this handler."""
        raise NotImplementedError("Subclasses must implement this method.")
