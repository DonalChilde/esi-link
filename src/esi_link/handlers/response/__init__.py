"""Response Handlers for ESI Link."""

from esi_link.handlers.response.debug_file_saver import DebugFileSaverResponseHandler
from esi_link.handlers.response.detailed_file_saver import (
    DetailedFileSaverResponseHandler,
)
from esi_link.handlers.response.dummy_handler import DummyResponseHandler
from esi_link.handlers.response.standard_file_saver import (
    StandardFileSaverResponseHandler,
)
from esi_link.models_and_protocols import ResponseHandlerProtocol

builtin_response_handlers: dict[str, type[ResponseHandlerProtocol]] = {
    DummyResponseHandler.name: DummyResponseHandler,
    DetailedFileSaverResponseHandler.name: DetailedFileSaverResponseHandler,
    DebugFileSaverResponseHandler.name: DebugFileSaverResponseHandler,
    StandardFileSaverResponseHandler.name: StandardFileSaverResponseHandler,
}
from esi_link.handlers.response.manager import ResponseHandlerManager

__all__ = [
    "builtin_response_handlers",
    "ResponseHandlerManager",
    "DebugFileSaverResponseHandler",
    "DetailedFileSaverResponseHandler",
    "StandardFileSaverResponseHandler",
]
