"""Response Handlers for ESI Link."""
###########################################################################
# ResponseHandlerProtocol Implementations
###########################################################################

import json
import logging
from pathlib import Path
from string import Template
from typing import Any, Self

from whenever import Instant

from esi_link.models import (
    EsiRequest,
    EsiResponse,
    HandlerConfig,
    HandlerConfigError,
    HandlerManagerProtocol,
    InvalidHandlerError,
    ResponseHandlerError,
    ResponseHandlerProtocol,
)

logger = logging.getLogger(__name__)

# TODO: improve response handler descriptions, esp re: tokens available for file paths
# Available tokens:
# - OPERATION_ID: The operation ID of the request
# - REQUEST_ID: The request ID of the request
# - NOW: The current timestamp in ISO 8601 format
# - HOME: The user's home directory
# - PATH_PARAMETERS: All path parameters from the request (uppercase)
# - QUERY_PARAMETERS: All query parameters from the request (uppercase)
# - CHARACTER_ID: The character ID from the auth parameters (if present)
# - CLIENT_ALIAS: The client alias from the auth parameters (if present)


# class KeepHttpResponseHandler(ResponseHandlerProtocol):
#     """A response handler that keeps the full HTTP response in the response context."""

#     name: str = "esi-link.keep_http_response"

#     async def handle_response(
#         self,
#         ctx: ResponseContext,
#         http_response: HttpResponse,
#         request: EsiRequest,
#     ) -> None:
#         ctx.response_data.http_responses[request.request_id] = (request, http_response)

#     @classmethod
#     def from_config(cls, config: HandlerConfig) -> "KeepHttpResponseHandler":
#         return cls()

#     @classmethod
#     def example_config(cls) -> tuple[HandlerConfig, str]:
#         """Return an example configuration for this handler, with a text description.

#         Example does not have to be a valid config, but should illustrate the main options.
#         """
#         example = HandlerConfig(name=cls.name, config={})
#         description = (
#             "Keeps the full HTTP response in the response context under "
#             "http_responses[query_id]. No configuration options are needed."
#         )
#         return example, description

#     @classmethod
#     def validate_config(cls, config: HandlerConfig) -> None:
#         if not config.name.startswith("esi-link."):
#             raise InvalidHandlerError(
#                 "Handler name must be in the 'esi-link.' namespace.",
#                 handler_name=config.name,
#                 response=None,
#             )


class FileOutMixin:
    """Mixin class for handlers that write to files."""

    def tokens(self, request: EsiRequest) -> dict[str, Any]:
        """Return a dict of tokens for str.format replacement in file paths."""
        token_values: dict[str, Any] = {
            "OPERATION_ID": request.operation_id,
            "REQUEST_ID": request.request_id,
            "NOW": FileSafeInstantNowIso(),
            "HOME": Path.home(),
        }
        token_values.update(
            {key.upper(): value for key, value in request.path_parameters.items()}
        )
        token_values.update(
            {key.upper(): value for key, value in request.query_parameters.items()}
        )
        if request.auth_parameters:
            token_values.update(
                {
                    "CHARACTER_ID": request.auth_parameters.character_id,
                    "CLIENT_ALIAS": request.auth_parameters.client_alias,
                }
            )
        return token_values

    def format_path(
        self,
        path_template: str,
        request: EsiRequest,
        extra_tokens: dict[str, Any] | None = None,
    ) -> Path:
        """Format a file path template with tokens from the request."""
        tokens = self.tokens(request)
        if extra_tokens:
            tokens.update(extra_tokens)
        str_template = Template(path_template)
        resolved_template = str_template.safe_substitute(**tokens)
        path_out = Path(resolved_template).resolve()
        path_out.parent.mkdir(parents=True, exist_ok=True)
        return path_out


class EsiResponseDataToFileHandler(ResponseHandlerProtocol, FileOutMixin):
    """A response handler that saves the JSON response data to a file."""

    name: str = "esi-link.esi_response_data_to_file"

    def __init__(self, file_path: str, overwrite: bool = False) -> None:
        """Initialize the EsiResponseDataToFileHandler."""
        self._file_path = file_path
        self._overwrite = overwrite

    async def handle_response(
        self,
        esi_response: EsiResponse,
    ) -> None:
        """Handle the response by saving the JSON data to a file."""
        try:
            http_response = esi_response.http_response
            if http_response is not None:
                path_out = self.format_path(self._file_path, esi_response.request)
                if not self._overwrite and path_out.exists():
                    raise ResponseHandlerError(
                        f"File {path_out} already exists. Use overwrite=True to overwrite.",
                        handler_name=self.name,
                        response=esi_response,
                    )
                with open(path_out, "w") as file:
                    json.dump(http_response.json_data, file, indent=2)
            else:
                raise ResponseHandlerError(
                    "httpResponse is None, nothing to save.",
                    handler_name=self.name,
                    response=esi_response,
                )
        except Exception as e:
            # Capture errors and log them in the esi_response error messages.
            msg = f"Error writing response data to file: {e!r}"
            esi_response.error_messages.append(msg)
            logger.error(msg)

    @classmethod
    def from_config(cls, config: HandlerConfig) -> Self:
        """Create a handler instance from the provided configuration."""
        cls.validate_config(config)
        try:
            result = cls(
                file_path=config.config.get("file_path"),  # type: ignore
                overwrite=config.config.get("overwrite", False),
            )
            return result
        except Exception as e:
            raise HandlerConfigError(
                f"Error creating handler from config: {e}", handler_config=config
            ) from e

    @classmethod
    def example_config(cls) -> tuple[HandlerConfig, str]:
        """Return an example configuration for this handler, with a text description.

        Example does not have to be a valid config, but should illustrate the main options.
        """
        example = HandlerConfig(
            name=cls.name,
            config={
                "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-data.json",
                "overwrite": False,
            },
        )
        description = (
            "Saves the JSON data from an html response to the specified file path. "
            "The file_path string is required. file_path supports ${KEY} replacement, "
            "with the following tokens available:\n\n"
            "OPERATION_ID: The operation ID of the request\n"
            "REQUEST_ID: The request ID of the request\n"
            "NOW: The current timestamp in ISO 8601 format\n"
            "HOME: The user's home directory\n"
            "PATH_PARAMETERS: All path parameters from the request (uppercase)\n"
            "QUERY_PARAMETERS: All query parameters from the request (uppercase)\n"
            "CHARACTER_ID: The character ID from the auth parameters (if present)\n"
            "CLIENT_ALIAS: The client alias from the auth parameters (if present)\n"
        )
        return example, description

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        """Validate the handler configuration."""
        file_path = config.config.get("file_path")
        if file_path is None or not isinstance(file_path, str):
            raise HandlerConfigError(
                "file_path is required to exist and be a string in handler config.",
                handler_config=config,
            )
        overwrite = config.config.get("overwrite", None)
        if overwrite is None or not isinstance(overwrite, bool):
            raise HandlerConfigError(
                "overwrite must be a boolean in handler config.", handler_config=config
            )
        if not config.name == cls.name:
            raise HandlerConfigError(
                "Handler name must match the Handler being created.",
                handler_config=config,
            )


class EsiResponseToFile(ResponseHandlerProtocol, FileOutMixin):
    """A response handler that saves the esi response to a JSON file."""

    name: str = "esi-link.esi_response_to_file"

    def __init__(self, file_path: str, overwrite: bool = False) -> None:
        """Initialize the EsiResponseToFile handler."""
        self._file_path = file_path
        self._overwrite = overwrite

    async def handle_response(
        self,
        esi_response: EsiResponse,
    ) -> None:
        """Handle the response by saving the EsiResponse to a JSON file."""
        try:
            path_out = self.format_path(self._file_path, esi_response.request)
            if not self._overwrite and path_out.exists():
                raise ResponseHandlerError(
                    f"File {path_out} already exists. Use overwrite=True to overwrite.",
                    handler_name=self.name,
                    response=esi_response,
                )
            path_out.write_text(esi_response.model_dump_json(indent=2))
        except Exception as e:
            # Capture errors and log them in the esi_response error messages.
            msg = f"Error writing EsiResponse to file: {e!r}"
            esi_response.error_messages.append(msg)
            logger.error(msg)

    @classmethod
    def from_config(cls, config: HandlerConfig) -> Self:
        """Create a handler instance from the provided configuration."""
        cls.validate_config(config)
        try:
            result = cls(
                file_path=config.config.get("file_path"),  # type: ignore
                overwrite=config.config.get("overwrite", False),
            )
            return result
        except Exception as e:
            raise HandlerConfigError(
                f"Error creating handler from config: {e}", handler_config=config
            ) from e

    @classmethod
    def example_config(cls) -> tuple[HandlerConfig, str]:
        """Return an example configuration for this handler, with a text description.

        Example does not have to be a valid config, but should illustrate the main options.
        """
        example = HandlerConfig(
            name=cls.name,
            config={
                "file_path": "${HOME}/tmp/esi-link-data/responses/${NOW}-${OPERATION_ID}-response.json",
                "overwrite": False,
            },
        )
        description = (
            "Saves the html response to the specified file path. "
            "The file_path string is required. file_path supports ${KEY} replacement, "
            "with the following tokens available:\n\n"
            "OPERATION_ID: The operation ID of the request\n"
            "REQUEST_ID: The request ID of the request\n"
            "NOW: The current timestamp in ISO 8601 format\n"
            "HOME: The user's home directory\n"
            "PATH_PARAMETERS: All path parameters from the request (uppercase)\n"
            "QUERY_PARAMETERS: All query parameters from the request (uppercase)\n"
            "CHARACTER_ID: The character ID from the auth parameters (if present)\n"
            "CLIENT_ALIAS: The client alias from the auth parameters (if present)\n"
        )
        return example, description

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        """Validate the handler configuration."""
        file_path = config.config.get("file_path")
        if file_path is None or not isinstance(file_path, str):
            raise HandlerConfigError(
                "file_path is required to exist and be a string in handler config.",
                handler_config=config,
            )
        overwrite = config.config.get("overwrite", None)
        if overwrite is None or not isinstance(overwrite, bool):
            raise HandlerConfigError(
                "overwrite must be a boolean in handler config.", handler_config=config
            )
        if not config.name == cls.name:
            raise HandlerConfigError(
                "Handler name must match the Handler being created.",
                handler_config=config,
            )


class HandlerManager(HandlerManagerProtocol):
    """A simple handler manager implementation."""

    def __init__(self) -> None:
        """Initialize the handler manager and register built-in handlers."""
        self.handlers: dict[str, type[ResponseHandlerProtocol]] = {}
        self._register_builtin_handlers()

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        """Get a handler instance from the manager based on the provided config."""
        handler_cls = self.handlers.get(config.name)
        if not handler_cls:
            raise HandlerConfigError(
                f"Handler not found in registry: {config.name}", handler_config=config
            )
        return handler_cls.from_config(config)

    def register_handler(
        self, name: str, handler_cls: type[ResponseHandlerProtocol]
    ) -> None:
        """Register a handler class with the manager."""
        if not issubclass(handler_cls, ResponseHandlerProtocol):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise InvalidHandlerError(
                f"Handler class must implement ResponseHandlerProtocol: {name}"
            )
        self.handlers[name] = handler_cls

    def get_all_handlers(self) -> list[type[ResponseHandlerProtocol]]:
        """Return a list of all registered handler classes."""
        return list(self.handlers.values())

    def _register_builtin_handlers(self) -> None:
        # self.register_handler(KeepHttpResponseHandler.name, KeepHttpResponseHandler)
        self.register_handler(
            EsiResponseDataToFileHandler.name, EsiResponseDataToFileHandler
        )
        self.register_handler(EsiResponseToFile.name, EsiResponseToFile)


class FileSafeInstantNowIso:
    """A class to get the current instant in a file-safe format."""

    @classmethod
    def now(cls) -> str:
        """Return the current instant as a file-safe ISO string."""
        return Instant.now().format_iso().replace(":", "-").replace(".", "_")

    def __str__(self) -> str:
        """Return the current instant as a file-safe ISO string."""
        return self.now()
