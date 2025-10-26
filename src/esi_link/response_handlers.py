###########################################################################
# ResponseHandlerProtocol Implementations
###########################################################################


import json
import logging
from pathlib import Path
from typing import Any, Self

from whenever import Instant

from esi_link.models import (
    EsiRequest,
    HandlerConfig,
    HandlerConfigError,
    HandlerManagerProtocol,
    HttpResponse,
    InvalidHandlerError,
    ResponseContext,
    ResponseHandlerError,
    ResponseHandlerProtocol,
)

logger = logging.getLogger(__name__)


class KeepHttpResponseHandler(ResponseHandlerProtocol):
    """A response handler that keeps the full HTTP response in the response context."""

    name: str = "esi-link.keep_http_response"

    async def handle_response(
        self,
        ctx: ResponseContext,
        http_response: HttpResponse,
        request: EsiRequest,
    ) -> None:
        ctx.response_data.http_responses[request.request_id] = (request, http_response)

    @classmethod
    def from_config(cls, config: HandlerConfig) -> "KeepHttpResponseHandler":
        return cls()

    @classmethod
    def example_config(cls) -> tuple[HandlerConfig, str]:
        """Return an example configuration for this handler, with a text description.

        Example does not have to be a valid config, but should illustrate the main options.
        """
        example = HandlerConfig(name=cls.name, config={})
        description = (
            "Keeps the full HTTP response in the response context under "
            "http_responses[query_id]. No configuration options are needed."
        )
        return example, description

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        if not config.name.startswith("esi-link."):
            raise InvalidHandlerError(
                "Handler name must be in the 'esi-link.' namespace.",
                handler_name=config.name,
                response=None,
            )


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
        path_out = Path(path_template.format(**tokens))
        return path_out


class JsonFileResponseDataHandler(ResponseHandlerProtocol, FileOutMixin):
    """A response handler that saves the JSON response data to a file."""

    name: str = "esi-link.json_data_file"

    def __init__(self, file_path: str, overwrite: bool = False) -> None:
        self._file_path = file_path
        self._overwrite = overwrite

    async def handle_response(
        self,
        ctx: ResponseContext,
        http_response: HttpResponse,
        request: EsiRequest,
    ) -> None:
        if http_response.json_data is not None:
            path_out = self.format_path(self._file_path, request)
            path_out.parent.mkdir(parents=True, exist_ok=True)
            if not self._overwrite and path_out.exists():
                # TODO more specific exception for handlers with name of ahndleer and
                raise ResponseHandlerError(
                    f"File {path_out} already exists. Use overwrite=True to overwrite.",
                    handler_name=self.name,
                    response=http_response,
                )
            with open(path_out, "w") as file:
                json.dump(http_response.json_data, file, indent=2)

    # def tokens(self, request: EsiRequest) -> dict[str, Any]:
    #     """Return a dict of tokens for str.format replacement in file paths."""
    #     token_values: dict[str, Any] = {
    #         "OPERATION_ID": request.operation_id,
    #         "REQUEST_ID": request.request_id,
    #         "NOW": FileSafeInstantNowIso(),
    #         "HOME": Path.home(),
    #     }
    #     token_values.update(
    #         {key.upper(): value for key, value in request.path_parameters.items()}
    #     )
    #     token_values.update(
    #         {key.upper(): value for key, value in request.query_parameters.items()}
    #     )
    #     if request.auth_parameters:
    #         token_values.update(
    #             {
    #                 "CHARACTER_ID": request.auth_parameters.character_id,
    #                 "CLIENT_ALIAS": request.auth_parameters.client_alias,
    #             }
    #         )
    #     return token_values

    @classmethod
    def from_config(cls, config: HandlerConfig) -> Self:
        file_path_str = config.config.get("file_path")
        if not file_path_str:
            raise HandlerConfigError(
                "file_path is required in handler config.", handler_config=config
            )
        return cls(file_path=file_path_str)

    @classmethod
    def example_config(cls) -> tuple[HandlerConfig, str]:
        """Return an example configuration for this handler, with a text description.

        Example does not have to be a valid config, but should illustrate the main options.
        """
        example = HandlerConfig(
            name=cls.name,
            config={
                "file_path": "{HOME}/tmp/esi-link-data/responses/{NOW}-{OPERATION_ID}-data.json",
                "overwrite": False,
            },
        )
        description = (
            "Saves the JSON response to the specified file path. "
            "The file_path option is required. file_path supports str.format replacement "
            "with tokens for operation_id, request_id, now, and any path, query or auth parameters."
        )
        return example, description

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        if "file_path" not in config.config:
            raise HandlerConfigError(
                "file_path is required in handler config.", handler_config=config
            )
        if not config.name.startswith("esi-link."):
            raise HandlerConfigError(
                "Handler name must be in the 'esi-link.' namespace.",
                handler_config=config,
            )


class HandlerManager(HandlerManagerProtocol):
    """A simple handler manager implementation."""

    def __init__(self) -> None:
        self.handlers: dict[str, type[ResponseHandlerProtocol]] = {}
        self._register_builtin_handlers()

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        handler_cls = self.handlers.get(config.name)
        logger.info(
            "Available handlers: {handlers}".format(
                handlers="".join(self.handlers.keys())
            )
        )
        if not handler_cls:
            raise HandlerConfigError(
                f"Handler not found in registry: {config.name}", handler_config=config
            )
        return handler_cls.from_config(config)

    def register_handler(
        self, name: str, handler_cls: type[ResponseHandlerProtocol]
    ) -> None:
        if not issubclass(handler_cls, ResponseHandlerProtocol):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise InvalidHandlerError(
                f"Handler class must implement ResponseHandlerProtocol: {name}"
            )
        self.handlers[name] = handler_cls

    def _register_builtin_handlers(self) -> None:
        self.register_handler(KeepHttpResponseHandler.name, KeepHttpResponseHandler)
        self.register_handler(
            JsonFileResponseDataHandler.name, JsonFileResponseDataHandler
        )


class FileSafeInstantNowIso:
    """A class to get the current instant in a file-safe format."""

    @classmethod
    def now(cls) -> str:
        """Return the current instant as a file-safe ISO string."""
        return Instant.now().format_iso().replace(":", "-").replace(".", "_")

    def __str__(self) -> str:
        return self.now()
