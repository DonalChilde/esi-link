# from esi_link.handlers.response.dummy_handler import DummyResponseHandler
# from esi_link.models_and_protocols import (
#     ResponseHandlerConfig,
#     ResponseHandlerManagerProtocol,
#     ResponseHandlerProtocol,
# )


# class DummyResponseHandlerManager(ResponseHandlerManagerProtocol):
#     def get_handler(
#         self, config: ResponseHandlerConfig
#     ) -> ResponseHandlerProtocol | None:
#         """Get a response handler instance based on the handler config."""
#         return DummyResponseHandler(config=config)

#     def register_handler(self, handler_cls: type[ResponseHandlerProtocol]) -> None:
#         """Register a response handler."""
#         return None

#     def registered_handlers(self) -> dict[str, type[ResponseHandlerProtocol]]:
#         """Get a dictionary of registered handler classes by their names."""
#         return {DummyResponseHandler.name: DummyResponseHandler}

#     def validate_handler_config(self, config: ResponseHandlerConfig) -> None:
#         """Validate a response handler config."""
#         pass
