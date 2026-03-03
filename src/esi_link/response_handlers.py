"""Pre-defined response handlers."""

import logging
from copy import deepcopy
from pathlib import Path
from typing import Self

from esi_link.models import (
    EsiResponse,
    HandlerConfig,
    HandlerManagerProtocol,
    HandlerNotFoundError,
    InvalidHandlerConfigError,
    ResponseHandlerProtocol,
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Response Handlers
# ------------------------------------------------------------------------------


class DummyResponseHandler(ResponseHandlerProtocol):
    """A dummy response handler that does nothing."""

    name = "esi-link:dummy"

    async def handle_response(self, response: EsiResponse) -> None:
        """Handle the response by doing nothing."""
        pass

    @classmethod
    def from_config(cls, config: HandlerConfig) -> Self:
        """Create a DummyResponseHandler from a HandlerConfig."""
        return cls()


class SimpleSaveToDiskResponseHandler(ResponseHandlerProtocol):
    name = "esi-link:simple_save_to_disk"

    def __init__(
        self,
        output_dir: Path,
        overwrite: bool = False,
        config: HandlerConfig | None = None,
    ) -> None:
        """A response handler that saves the response to disk.

        This response handler saves the response to disk as a JSON file.
        The directory is supplied by the user, and the file name is generated from
        the request ID, operation_id, and response status code. The handler will not
        overwrite existing files by default, but this can be changed with the
        `overwrite` option.


        """
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.config: HandlerConfig | None = None

    @staticmethod
    def _check_directory(output_dir: str) -> Path:
        """Check if the output directory is valid, and create it if it doesn't exist."""
        if output_dir.startswith("/"):
            msg = (
                "output_dir must be a relative path - from home or current working directory, "
                "not an absolute path. Try `~/output/dir` or `output/dir` instead of `/output/dir`."
            )
            raise ValueError(msg)
        output_path = Path(output_dir).expanduser().resolve()
        if output_path.is_file():
            raise ValueError(
                f"output_dir '{output_dir}' resolves to a file, but must be a directory."
            )
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    async def handle_response(self, response: EsiResponse) -> None:
        """Handle the response by saving it to disk."""
        request_id = response.request.request_id
        operation_id = response.request.operation_id
        status_code = (
            response.http_response.status_code
            if response.http_response
            else "NO_RESPONSE"
        )
        output_file = (
            self.output_dir / f"{request_id}-{operation_id}-{status_code}.json"
        )

        if output_file.exists() and not self.overwrite:
            raise FileExistsError(
                f"File {output_file} already exists and overwrite is set to False."
            )

        with output_file.open("w") as f:
            f.write(response.model_dump_json(indent=2))

    @classmethod
    def from_config(cls, config: HandlerConfig) -> Self:
        """Create a SimpleSaveToDiskResponseHandler from a HandlerConfig.

        The directory can be:
        - a path relative to the current working directory (e.g. "output/dir")
        - or a path relative to the user's home directory (e.g. "~/output/dir").
        If the directory does not exist, it will be created.

        Example:
        ```json
        config = {
            "name": "esi-link:simple_save_to_disk",
            "config": {
                "output_dir": "/path/to/output/dir",
                "overwrite": false
            }
        }
        ```
        """
        output_dir = cls._check_directory(config.config["output_dir"])
        return cls(
            output_dir=output_dir, overwrite=config.config["overwrite"], config=config
        )

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        """Check the HandlerConfig for the required keys and their types."""
        check_required_keys(config, {"output_dir", "overwrite"})
        if not isinstance(config.config["output_dir"], str):
            raise ValueError("output_dir must be a string.")
        if not isinstance(config.config["overwrite"], bool):
            raise ValueError("overwrite must be a boolean.")


def check_required_keys(config: HandlerConfig, required_keys: set[str]) -> None:
    """Check the HandlerConfig for the required keys and their types."""
    keys = set(config.config.keys())
    missing_keys = required_keys - keys
    if missing_keys:
        raise ValueError(f"Missing required config keys: {missing_keys}")
    extra_keys = keys - required_keys
    if extra_keys:
        raise ValueError(f"Extra config keys not used by handler: {extra_keys}")


class DummyHandlerManager(HandlerManagerProtocol):
    """A dummy handler manager that does nothing."""

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        """Return a dummy handler for the given handler config."""
        return DummyResponseHandler()

    def register_handler(self, handler_cls: type[ResponseHandlerProtocol]) -> None:
        """Does Nothing, as this is a dummy handler manager."""
        pass

    def registered_handlers(self) -> dict[str, type[ResponseHandlerProtocol]]:
        """Return a dictionary with only the dummy handler registered."""
        return {DummyResponseHandler.name: DummyResponseHandler}

    def validate_handler_config(self, config: HandlerConfig) -> None:
        """Does Nothing, as this is a dummy handler manager."""
        pass


handler_lookup: dict[str, type[ResponseHandlerProtocol]] = {
    DummyResponseHandler.name: DummyResponseHandler,
    SimpleSaveToDiskResponseHandler.name: SimpleSaveToDiskResponseHandler,
}


class HandlerManager(HandlerManagerProtocol):
    """A manager for response handlers."""

    def __init__(self) -> None:
        """Initialize the handler manager."""
        self._handlers: dict[str, type[ResponseHandlerProtocol]] = handler_lookup

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        """Get a response handler instance based on the handler config."""
        if config.name not in self._handlers:
            error = HandlerNotFoundError(f"Handler '{config.name}' not found.", config)
            raise error
        return self._handlers[config.name].from_config(config)

    def register_handler(self, handler_cls: type[ResponseHandlerProtocol]) -> None:
        """Register a response handler."""
        self._handlers[handler_cls.name] = handler_cls

    def registered_handlers(self) -> dict[str, type[ResponseHandlerProtocol]]:
        """Get a dictionary of registered handler classes by their names."""
        return deepcopy(self._handlers)

    def validate_handler_config(self, config: HandlerConfig) -> None:
        """Validate a handler config by checking if the handler exists and then validating the config."""
        if config.name not in self._handlers:
            error = HandlerNotFoundError(f"Handler '{config.name}' not found.", config)
            raise error
        handler_cls = self._handlers[config.name]
        try:
            handler_cls.validate_config(config)
        except Exception as e:
            error = InvalidHandlerConfigError(
                f"Invalid config for handler '{config.name}': {e}", config=config
            )
            logger.exception("%s", error)
            raise error from e
