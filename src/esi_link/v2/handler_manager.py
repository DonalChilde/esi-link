"""Response handler manager implementation."""

from esi_link.v2.models import (
    HandlerConfig,
    HandlerManagerProtocol,
    ResponseHandlerProtocol,
)
from esi_link.v2.response_handlers import DummyResponseHandler


class DummyHandlerManager(HandlerManagerProtocol):
    """A dummy handler manager that does nothing."""

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        """Return a dummy handler for the given handler config."""
        return DummyResponseHandler()
