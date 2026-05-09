# """A dummy response group handler that does nothing bu log the call."""

# import logging
# from typing import Self

# from esi_link.handlers.response_group.group_handler_abc import ResponseGroupHandlerABC
# from esi_link.models_and_protocols import (
#     ResponseGroup,
#     ResponseGroupHandlerConfig,
# )

# logger = logging.getLogger(__name__)


# class DummyResponseGroupHandler(ResponseGroupHandlerABC):
#     """A dummy response group handler that does nothing."""

#     name = "esi-link:dummy_group_handler"

#     def __init__(self, config: ResponseGroupHandlerConfig) -> None:
#         """Initialize the DummyResponseGroupHandler."""
#         self.config = config

#     async def __call__(self, response_group: ResponseGroup) -> ResponseGroup:
#         """Handle the responses by doing nothing."""
#         logger.info(
#             "DummyResponseGroupHandler called for request group %s with %s responses, config: %r",
#             response_group.request_group.group_id,
#             len(response_group.responses),
#             self.config.model_dump(),
#         )
#         return response_group

#     @classmethod
#     def from_config(cls, config: ResponseGroupHandlerConfig) -> Self:
#         """Create a DummyResponseGroupHandler from a ResponseGroupHandlerConfig."""
#         return cls(config=config)

#     @classmethod
#     def validate_config(cls, config: ResponseGroupHandlerConfig) -> None:
#         """Validate the ResponseGroupHandlerConfig for a DummyResponseGroupHandler."""
#         pass
