"""ResponseGroupHandler implementations and manager."""

import logging
from copy import deepcopy
from typing import Self

from esi_link.v3.handlers.errors import (
    HandlerCreationError,
    HandlerNotFoundError,
    HandlerValidationError,
)
from esi_link.v3.models import RequestGroup, Response, ResponseGroupHandlerConfig
from esi_link.v3.protocols import (
    ResponseGroupHandlerManagerProtocol,
    ResponseGroupHandlerProtocol,
)

logger = logging.getLogger(__name__)


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


builtin_response_group_handlers: dict[str, type[ResponseGroupHandlerProtocol]] = {
    DummyResponseGroupHandler.name: DummyResponseGroupHandler,
}


class DummyResponseGroupHandlerManager(ResponseGroupHandlerManagerProtocol):
    """A dummy response group handler manager that only manages the DummyResponseGroupHandler."""

    def get_handler(
        self, config: ResponseGroupHandlerConfig
    ) -> ResponseGroupHandlerProtocol:
        """Get a response group handler for the given config."""
        return DummyResponseGroupHandler(config=config)

    def register_handler(self, handler_cls: type[ResponseGroupHandlerProtocol]) -> None:
        """Register a response group handler class."""
        pass

    def registered_handlers(self) -> dict[str, type[ResponseGroupHandlerProtocol]]:
        """Get a dictionary of registered response group handler classes."""
        return {DummyResponseGroupHandler.name: DummyResponseGroupHandler}

    def validate_handler_config(self, config: ResponseGroupHandlerConfig) -> None:
        """Validate a response group handler configuration."""
        pass


class ResponseGroupHandlerManager(ResponseGroupHandlerManagerProtocol):
    """A response group handler manager that manages response group handlers."""

    def __init__(self) -> None:
        """Initialize the ResponseGroupHandlerManager."""
        self._handlers: dict[str, type[ResponseGroupHandlerProtocol]] = {}
        self._handlers.update(builtin_response_group_handlers)

    def get_handler(
        self, config: ResponseGroupHandlerConfig
    ) -> ResponseGroupHandlerProtocol:
        """Get a response group handler for the given config."""
        if config.name not in self._handlers:
            error = HandlerNotFoundError(
                f"Handler '{config.name}' not found.", config.model_dump()
            )
            raise error
        return self._handlers[config.name].from_config(config)

    def register_handler(self, handler_cls: type[ResponseGroupHandlerProtocol]) -> None:
        """Register a response group handler class."""
        if handler_cls.name in self._handlers:
            raise HandlerCreationError(
                f"Handler '{handler_cls.name}' is already registered."
            )
        self._handlers[handler_cls.name] = handler_cls

    def registered_handlers(self) -> dict[str, type[ResponseGroupHandlerProtocol]]:
        """Get a dictionary of registered response group handler classes."""
        return deepcopy(self._handlers)

    def validate_handler_config(self, config: ResponseGroupHandlerConfig) -> None:
        """Validate a handler config by checking if the handler exists and then validating the config."""
        if config.name not in self._handlers:
            error = HandlerNotFoundError(
                f"Handler '{config.name}' not found.", config.model_dump()
            )
            raise error
        handler_cls = self._handlers[config.name]
        # Handlers should raise their own validation errors, so we don't need to catch
        # them here, but we will catch any unexpected errors and raise a HandlerValidationError
        # for clarity.
        try:
            handler_cls.validate_config(config)
        except HandlerValidationError as e:
            raise e
        except Exception as e:
            error = HandlerValidationError(
                f"An error occurred while validating the handler config: {e}",
                config=config.model_dump(),
            )
            raise error from e
