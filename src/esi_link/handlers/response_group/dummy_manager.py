from esi_link.handlers.response_group.dummy_handler import (
    DummyResponseGroupHandler,
)
from esi_link.models_and_protocols import (
    ResponseGroupHandlerConfig,
    ResponseGroupHandlerManagerProtocol,
    ResponseGroupHandlerProtocol,
)


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
