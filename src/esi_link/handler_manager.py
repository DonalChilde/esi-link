"""Response handler manager implementation."""

from esi_link.models import (
    HandlerConfig,
    HandlerManagerProtocol,
    ResponseHandlerProtocol,
)
from esi_link.response_handlers import DummyResponseHandler


class DummyHandlerManager(HandlerManagerProtocol):
    """A dummy handler manager that does nothing."""

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        """Return a dummy handler for the given handler config."""
        return DummyResponseHandler()

    def register_handler(
        self, name: str, handler_cls: type[ResponseHandlerProtocol]
    ) -> None:
        """Does Nothing, as this is a dummy handler manager."""

    ...

    def get_all_handlers(self) -> list[type[ResponseHandlerProtocol]]:
        """Does Nothing, as this is a dummy handler manager."""
        ...

    def validate_handler_config(self, config: HandlerConfig) -> None:
        """Does Nothing, as this is a dummy handler manager."""
        ...
