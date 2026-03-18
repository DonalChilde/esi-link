"""Abstract base class for response handlers."""

from typing import Self

from esi_link.models_and_protocols import (
    ResponseGroup,
    ResponseGroupHandlerConfig,
    ResponseGroupHandlerProtocol,
)


class ResponseGroupHandlerABC(ResponseGroupHandlerProtocol):
    """Abstract base class for response group handlers.

    This class defines the interface for response group handlers, and provides some common
    functionality. Subclasses must implement the `__call__` method to handle the
    response group.
    """

    name = "esi-link:response_group_handler_abc"

    def __init__(self, config: ResponseGroupHandlerConfig) -> None:
        self.config = config

    async def __call__(self, response_group: ResponseGroup) -> ResponseGroup:
        """Handle the response group."""
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    def from_config(cls, config: ResponseGroupHandlerConfig) -> Self:
        """Create a response group handler from a ResponseGroupHandlerConfig."""
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    def validate_config(cls, config: ResponseGroupHandlerConfig) -> None:
        """Validate the ResponseGroupHandlerConfig for this handler."""
        raise NotImplementedError("Subclasses must implement this method.")
