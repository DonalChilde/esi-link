from typing import Any

from esi_link.v3.errors import EsiLinkError


class ResponseHandlerError(EsiLinkError):
    """Base class for errors raised by response handlers."""

    pass


class HandlerCreationError(ResponseHandlerError):
    """Raised when there is an error creating a response handler from a config."""

    pass


class HandlerValidationError(ResponseHandlerError):
    """Raised when there is an error validating a response handler config."""

    def __init__(self, message: str, config: dict[str, Any]) -> None:
        super().__init__(message)
        self.config = config

    def __str__(self) -> str:
        return f"{super().__str__()} | Config: {self.config!r}"


class HandlerNotFoundError(ResponseHandlerError):
    """Raised when a handler is not found for a given config."""

    def __init__(self, message: str, config: dict[str, Any]) -> None:
        super().__init__(message)
        self.config = config

    def __str__(self) -> str:
        return f"{super().__str__()} | Config: {self.config!r}"
