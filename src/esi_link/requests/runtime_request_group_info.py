"""Module for generating runtime request group information from ESI request groups."""

from esi_link.handlers.response_group.manager import (
    ResponseGroupHandlerManager,
)
from esi_link.models_and_protocols import (
    RequestGroup,
    RequestGroupMetrics,
    ResponseGroupHandlerManagerProtocol,
    ResponseGroupHandlerProtocol,
    RuntimeGroupInfo,
    RuntimeGroupInfoGeneratorProtocol,
)


class RuntimeRequestGroupInfoGenerator(RuntimeGroupInfoGeneratorProtocol):
    def __init__(
        self,
        response_group_handler_manager: ResponseGroupHandlerManagerProtocol
        | None = None,
    ) -> None:
        """Initialize the RuntimeRequestGroupInfoGenerator."""
        self.response_group_handler_manager = (
            response_group_handler_manager or ResponseGroupHandlerManager()
        )

    def __call__(self, request_group: RequestGroup) -> RuntimeGroupInfo:
        """Generate the RuntimeGroupInfo for a given RequestGroup."""
        handlers: list[ResponseGroupHandlerProtocol] = []
        for handler_config in request_group.response_group_handlers:
            self.response_group_handler_manager.validate_handler_config(handler_config)
            handler = self.response_group_handler_manager.get_handler(handler_config)
            handlers.append(handler)
        result = RuntimeGroupInfo(
            metrics=RequestGroupMetrics(),
            response_group_handlers=handlers,
        )
        return result
