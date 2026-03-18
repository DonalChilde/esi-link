from copy import deepcopy

from esi_link.handlers.errors import (
    HandlerCreationError,
    HandlerNotFoundError,
    HandlerValidationError,
)
from esi_link.handlers.response_group import (
    builtin_response_group_handlers,
)
from esi_link.models_and_protocols import (
    ResponseGroupHandlerConfig,
    ResponseGroupHandlerManagerProtocol,
    ResponseGroupHandlerProtocol,
)


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
