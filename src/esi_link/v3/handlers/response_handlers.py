"""Response handlers for ESI Link."""

import logging
from copy import deepcopy
from pathlib import Path
from typing import Self

from esi_link.v3.handlers.errors import (
    HandlerCreationError,
    HandlerNotFoundError,
    HandlerValidationError,
)
from esi_link.v3.helpers.save_text_file import save_text_file
from esi_link.v3.models import Response, ResponseHandlerConfig
from esi_link.v3.protocols import (
    ResponseHandlerManagerProtocol,
    ResponseHandlerProtocol,
)

logger = logging.getLogger(__name__)


class DummyResponseHandler(ResponseHandlerProtocol):
    """A dummy response handler that does nothing."""

    name = "esi-link:dummy"

    def __init__(self, config: ResponseHandlerConfig) -> None:
        """Initialize the DummyResponseHandler."""
        self.config = config

    async def __call__(self, response: Response) -> Response:
        """Handle the response by doing nothing."""
        if response.http_response is None:
            logger.info(
                "DummyResponseHandler called with response with no http_response, name: %s, config: %r",
                response.request.request_id,
                self.config.model_dump(),
            )
            return response
        logger.info(
            "DummyResponseHandler called with config: %r, for url: %s",
            self.config.model_dump(),
            response.http_response.url,
        )
        return response

    @classmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        """Create a DummyResponseHandler from a HandlerConfig."""
        return cls(config=config)

    @classmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        """Validate the HandlerConfig for a DummyResponseHandler."""
        pass


class SimpleSaveToDiskResponseHandler(ResponseHandlerProtocol):
    name = "esi-link:simple_save_to_disk"

    def __init__(
        self,
        config: ResponseHandlerConfig,
        output_dir: Path,
        overwrite: bool = False,
    ) -> None:
        """A response handler that saves the response to disk.

        This response handler saves the response to disk as a JSON file.
        The directory is supplied by the user, and the file name is generated from
        the request ID, operation_id, and response status code. The handler will not
        overwrite existing files by default, but this can be changed with the
        `overwrite` option.


        """
        self.config = config
        self.output_dir = output_dir
        self.overwrite = overwrite

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

    async def __call__(self, response: Response) -> Response:
        """Handle the response by saving it to disk."""
        request_id = response.request.request_id
        operation_id = response.request.operation_id
        status_code = (
            response.http_response.status_code
            if response.http_response
            else "NO_RESPONSE"
        )
        file_path = save_text_file(
            text=response.model_dump_json(indent=2),
            output_path=self.output_dir,
            file_name=f"{request_id}-{operation_id}-{status_code}.json",
            overwrite=self.overwrite,
        )
        logger.info(
            "Response saved to %s for %s-%s-%s",
            file_path,
            request_id,
            operation_id,
            status_code,
        )
        return response

    @classmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        """Create a SimpleSaveToDiskResponseHandler from a ResponseHandlerConfig.

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
        try:
            output_dir = cls._check_directory(config.config["output_dir"])
            overwrite = config.config.get("overwrite", False)
        except KeyError as e:
            raise HandlerCreationError(f"Missing required config key: {e}") from e
        except Exception as e:
            raise HandlerCreationError(
                f"An error occurred while creating the handler: {e}"
            ) from e
        return cls(output_dir=output_dir, overwrite=overwrite, config=config)

    @classmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        """Check the ResponseHandlerConfig for the required keys and their types."""
        check_required_keys(config, {"output_dir", "overwrite"})
        if not isinstance(config.config["output_dir"], str):
            raise HandlerValidationError(
                "output_dir must be a string.", config=config.model_dump()
            )
        if not isinstance(config.config["overwrite"], bool):
            raise HandlerValidationError(
                "overwrite must be a boolean.", config=config.model_dump()
            )


def check_required_keys(config: ResponseHandlerConfig, required_keys: set[str]) -> None:
    """Check the ResponseHandlerConfig for the required keys and their types."""
    keys = set(config.config.keys())
    missing_keys = required_keys - keys
    if missing_keys:
        raise HandlerValidationError(
            f"Missing required config keys: {missing_keys}", config=config.model_dump()
        )
    extra_keys = keys - required_keys
    if extra_keys:
        raise HandlerValidationError(
            f"Extra config keys not used by handler: {extra_keys}",
            config=config.model_dump(),
        )


class DummyResponseHandlerManager(ResponseHandlerManagerProtocol):
    def get_handler(
        self, config: ResponseHandlerConfig
    ) -> ResponseHandlerProtocol | None:
        """Get a response handler instance based on the handler config."""
        return DummyResponseHandler(config=config)

    def register_handler(self, handler_cls: type[ResponseHandlerProtocol]) -> None:
        """Register a response handler."""
        return None

    def registered_handlers(self) -> dict[str, type[ResponseHandlerProtocol]]:
        """Get a dictionary of registered handler classes by their names."""
        return {DummyResponseHandler.name: DummyResponseHandler}

    def validate_handler_config(self, config: ResponseHandlerConfig) -> None:
        """Validate a response handler config."""
        pass


builtin_response_handlers: dict[str, type[ResponseHandlerProtocol]] = {
    DummyResponseHandler.name: DummyResponseHandler,
    SimpleSaveToDiskResponseHandler.name: SimpleSaveToDiskResponseHandler,
}


class ResponseHandlerManager(ResponseHandlerManagerProtocol):
    """A manager for response handlers."""

    def __init__(self) -> None:
        """Initialize the handler manager."""
        self._handlers: dict[str, type[ResponseHandlerProtocol]] = {}
        self._handlers.update(builtin_response_handlers)

    def get_handler(self, config: ResponseHandlerConfig) -> ResponseHandlerProtocol:
        """Get a response handler instance based on the handler config."""
        if config.name not in self._handlers:
            error = HandlerNotFoundError(
                f"Handler '{config.name}' not found.", config.model_dump()
            )
            raise error
        return self._handlers[config.name].from_config(config)

    def register_handler(self, handler_cls: type[ResponseHandlerProtocol]) -> None:
        """Register a response handler."""
        if handler_cls.name in self._handlers:
            raise HandlerCreationError(
                f"Handler '{handler_cls.name}' is already registered."
            )
        self._handlers[handler_cls.name] = handler_cls

    def registered_handlers(self) -> dict[str, type[ResponseHandlerProtocol]]:
        """Get a dictionary of registered handler classes by their names."""
        return deepcopy(self._handlers)

    def validate_handler_config(self, config: ResponseHandlerConfig) -> None:
        """Validate a handler config by checking if the handler exists and then validating the config."""
        if config.name not in self._handlers:
            error = HandlerNotFoundError(
                f"Handler '{config.name}' not found.", config.model_dump()
            )
            raise error
        handler_cls = self._handlers[config.name]
        # Handlers should raise their own validation errors, so we don't need to catch
        # them here, but we will catch any unexpected errors and raise a HandlerValidationError
        # for clarity.
        try:
            handler_cls.validate_config(config)
        except HandlerValidationError as e:
            raise e
        except Exception as e:
            error = HandlerValidationError(
                f"An error occurred while validating the handler config: {e}",
                config=config.model_dump(),
            )
            raise error from e
