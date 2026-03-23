"""Abstract base class for response handlers."""

from abc import abstractmethod
from typing import Self

from esi_link.handlers.errors import HandlerBadResponseError
from esi_link.handlers.response.helpers import check_available_keys
from esi_link.models_and_protocols import (
    Response,
    ResponseHandlerConfig,
    ResponseHandlerProtocol,
)


class ResponseHandlerABC(ResponseHandlerProtocol):
    """Abstract base class for response handlers.

    This class defines the interface for response handlers, and provides some common
    functionality. Subclasses must implement the `__call__` method to handle the
    response.
    """

    name = "esi-link:response_handler_abc"

    def __init__(self, config: ResponseHandlerConfig) -> None:
        self.config = config

    @abstractmethod
    async def __call__(self, response: Response) -> Response:
        """Handle the response.

        An exception during handling should not raise, but should be caught and logged.
        The messages from any exceptions should be appended to the response's handler_exception_messages,
        and the exceptions themselves should be appended to the response's exceptions list.
        """
        try:
            pass
        except Exception as e:
            response.handler_exception_messages.append(str(e))
            response.exceptions.append(e)

        # return response
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    @abstractmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        """Create a response handler from a ResponseHandlerConfig."""
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    @abstractmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        """Validate the ResponseHandlerConfig for this handler."""
        raise NotImplementedError("Subclasses must implement this method.")

    @staticmethod
    def _fail_on_no_http_response(response: Response) -> None:
        """Check that the response contains the expected http_response for this handler."""
        if response.http_response is None:
            raise HandlerBadResponseError(
                "Response is missing http_response required for templated filename handler.",
                response_data={
                    "request_id": str(response.request.request_id),
                    "exception_messages": response.network_exception_messages,
                },
            )

    @staticmethod
    def _check_available_keys(
        config: ResponseHandlerConfig, required_keys: set[str]
    ) -> None:
        """Check the ResponseHandlerConfig for the required keys and their types."""
        check_available_keys(config, required_keys)
