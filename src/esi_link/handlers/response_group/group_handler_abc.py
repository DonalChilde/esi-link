# """Abstract base class for response handlers."""

# from abc import abstractmethod
# from typing import Self

# from esi_link.handlers.errors import HandlerValidationError
# from esi_link.models_and_protocols import (
#     ResponseGroup,
#     ResponseGroupHandlerConfig,
#     ResponseGroupHandlerProtocol,
# )


# class ResponseGroupHandlerABC(ResponseGroupHandlerProtocol):
#     """Abstract base class for response group handlers.

#     This class defines the interface for response group handlers, and provides some common
#     functionality. Subclasses must implement the `__call__` method to handle the
#     response group.
#     """

#     name = "esi-link:response_group_handler_abc"

#     def __init__(self, config: ResponseGroupHandlerConfig) -> None:
#         self.config = config

#     async def __call__(self, response_group: ResponseGroup) -> ResponseGroup:
#         """Handle the response_group.

#         An exception during handling should not raise, but should be caught and logged.
#         The messages from any exceptions should be appended to the response's handler_exception_messages,
#         and the exceptions themselves should be appended to the response's exceptions list.
#         """
#         try:
#             await self.handle_response_group(response_group)
#         except Exception as e:
#             response_group.group_handler_exception_messages.append(str(e))
#             response_group.exceptions.append(e)
#         return response_group

#     @abstractmethod
#     async def handle_response_group(
#         self, response_group: ResponseGroup
#     ) -> ResponseGroup:
#         """Handle the response group with error handling."""
#         raise NotImplementedError("Subclasses must implement this method.")

#     @classmethod
#     @abstractmethod
#     def from_config(cls, config: ResponseGroupHandlerConfig) -> Self:
#         """Create a response group handler from a ResponseGroupHandlerConfig."""
#         raise NotImplementedError("Subclasses must implement this method.")

#     @classmethod
#     @abstractmethod
#     def validate_config(cls, config: ResponseGroupHandlerConfig) -> None:
#         """Validate the ResponseGroupHandlerConfig for this handler."""
#         # No validation of config possible because config has no settings.
#         pass

#     @staticmethod
#     def _check_available_keys(
#         config: ResponseGroupHandlerConfig, required_keys: set[str]
#     ) -> None:
#         """Check that the required keys are available in the response group."""
#         keys = set(config.config.keys())
#         missing_keys = required_keys - keys
#         if missing_keys:
#             raise HandlerValidationError(
#                 f"Missing required config keys: {missing_keys}",
#                 config=config.model_dump(),
#             )
#         extra_keys = keys - required_keys
#         if extra_keys:
#             raise HandlerValidationError(
#                 f"Extra config keys not used by handler: {extra_keys}",
#                 config=config.model_dump(),
#             )
