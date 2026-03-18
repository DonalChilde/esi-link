from esi_link.handlers.response.dummy_handler import DummyResponseHandler
from esi_link.handlers.response.simple_save_response import (
    SimpleSaveToDiskResponseHandler,
)
from esi_link.handlers.response.templated_filename_handler import (
    TemplatedFilenameResponseHandler,
)
from esi_link.models_and_protocols import ResponseHandlerProtocol

builtin_response_handlers: dict[str, type[ResponseHandlerProtocol]] = {
    DummyResponseHandler.name: DummyResponseHandler,
    SimpleSaveToDiskResponseHandler.name: SimpleSaveToDiskResponseHandler,
    TemplatedFilenameResponseHandler.name: TemplatedFilenameResponseHandler,
}
from esi_link.handlers.response.manager import ResponseHandlerManager

__all__ = ["builtin_response_handlers", "ResponseHandlerManager"]
