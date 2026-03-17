import logging

from esi_link.v3.models import RequestGroup
from esi_link.v3.protocols import (
    RequestGroupValidatorProtocol,
    ResponseGroupHandlerManagerProtocol,
)
from esi_link.v3.validation.errors import RequestGroupValidationError

logger = logging.getLogger(__name__)


class RequestGroupValidator(RequestGroupValidatorProtocol):
    def __init__(
        self,
        response_group_handler_manager: ResponseGroupHandlerManagerProtocol,
    ) -> None:
        """Initialize the RequestGroupValidator.

        Args:
            response_group_handler_manager: The response group handler manager to validate response group handler configs against.
        """
        self.response_group_handler_manager = response_group_handler_manager

    def __call__(self, request_group: RequestGroup) -> None:
        """Validate the RequestGroup."""
        try:
            for handler_config in request_group.response_group_handlers:
                self.response_group_handler_manager.validate_handler_config(
                    handler_config
                )
        except Exception as e:
            logger.error(
                f"ESI request group validation failed: {e}, request group: {request_group.group_id}"
            )
            raise RequestGroupValidationError(
                f"ESI request group validation failed: {e}. See logs for details.",
                str(request_group.group_id),
            ) from e
