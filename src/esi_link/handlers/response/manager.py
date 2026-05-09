# from copy import deepcopy

# from esi_link.handlers.errors import (
#     HandlerCreationError,
#     HandlerNotFoundError,
#     HandlerValidationError,
# )
# from esi_link.handlers.response import builtin_response_handlers
# from esi_link.models_and_protocols import (
#     ResponseHandlerConfig,
#     ResponseHandlerManagerProtocol,
#     ResponseHandlerProtocol,
# )


# class ResponseHandlerManager(ResponseHandlerManagerProtocol):
#     """A manager for response handlers."""

#     def __init__(self) -> None:
#         """Initialize the handler manager."""
#         self._handlers: dict[str, type[ResponseHandlerProtocol]] = {}
#         self._handlers.update(builtin_response_handlers)

#     def get_handler(self, config: ResponseHandlerConfig) -> ResponseHandlerProtocol:
#         """Get a response handler instance based on the handler config."""
#         if config.name not in self._handlers:
#             error = HandlerNotFoundError(
#                 f"Handler '{config.name}' not found.", config.model_dump()
#             )
#             raise error
#         return self._handlers[config.name].from_config(config)

#     def register_handler(self, handler_cls: type[ResponseHandlerProtocol]) -> None:
#         """Register a response handler."""
#         if handler_cls.name in self._handlers:
#             raise HandlerCreationError(
#                 f"Handler '{handler_cls.name}' is already registered."
#             )
#         self._handlers[handler_cls.name] = handler_cls

#     def registered_handlers(self) -> dict[str, type[ResponseHandlerProtocol]]:
#         """Get a dictionary of registered handler classes by their names."""
#         return deepcopy(self._handlers)

#     def validate_handler_config(self, config: ResponseHandlerConfig) -> None:
#         """Validate a handler config by checking if the handler exists and then validating the config."""
#         if config.name not in self._handlers:
#             error = HandlerNotFoundError(
#                 f"Handler '{config.name}' not found.", config.model_dump()
#             )
#             raise error
#         handler_cls = self._handlers[config.name]
#         # Handlers should raise their own validation errors, so we don't need to catch
#         # them here, but we will catch any unexpected errors and raise a HandlerValidationError
#         # for clarity.
#         try:
#             handler_cls.validate_config(config)
#         except HandlerValidationError as e:
#             raise e
#         except Exception as e:
#             error = HandlerValidationError(
#                 f"An error occurred while validating the handler config: {e}",
#                 config=config.model_dump(),
#             )
#             raise error from e
