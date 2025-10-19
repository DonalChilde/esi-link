###########################################################################
# ResponseHandlerProtocol Implementations
###########################################################################


from pathlib import Path

from whenever import Instant

from esi_link.models import (
    EsiRequest,
    HandlerConfig,
    HandlerManagerProtocol,
    HandlerNotFoundError,
    HttpResponse,
    InvalidHandlerError,
    ResponseContext,
    ResponseHandlerProtocol,
)


class KeepHttpResponseHandler(ResponseHandlerProtocol):
    """A response handler that keeps the full HTTP response in the response context."""

    name: str = "esi-link.keep_http_response"

    async def handle_response(
        self,
        ctx: ResponseContext,
        http_response: HttpResponse,
        request: EsiRequest,
    ) -> None:
        ctx.response_data.http_responses[request.query_id] = (request, http_response)

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
                "Handler name must be in the 'esi-link.' namespace."
            )


class JsonFileResponseHandler(ResponseHandlerProtocol):
    """A response handler that saves the JSON response to a file."""

    name: str = "esi-link.json_data_file"

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    async def handle_response(
        self,
        ctx: ResponseContext,
        http_response: HttpResponse,
        request: EsiRequest,
    ) -> None:
        if http_response.json_data is not None:
            path_out = Path(self._file_path.format(**self.tokens(request)))
            path_out.parent.mkdir(parents=True, exist_ok=True)
            with open(path_out, "w") as file:
                import json

                json.dump(http_response.json_data, file, indent=2)

    def tokens(self, request: EsiRequest) -> dict[str, str]:
        """Return a dict of tokens for str.format replacement in file paths."""
        token_values = {
            "operation_id": request.operation_id,
            "query_id": str(request.query_id),
            "now": Instant.now().format_iso(),
        }
        token_values.update(
            {key: str(value) for key, value in request.path_parameters.items()}
        )
        token_values.update(
            {key: str(value) for key, value in request.query_parameters.items()}
        )
        if request.auth_parameters:
            token_values.update(
                {
                    "character_id": str(request.auth_parameters.character_id),
                    "client_id": str(request.auth_parameters.client_id),
                    "client_alias": request.auth_parameters.client_alias,
                }
            )
        return token_values

    @classmethod
    def from_config(cls, config: HandlerConfig) -> "JsonFileResponseHandler":
        file_path_str = config.config.get("file_path")
        if not file_path_str:
            raise InvalidHandlerError("file_path is required in handler config.")
        return cls(file_path=file_path_str)

    @classmethod
    def example_config(cls) -> tuple[HandlerConfig, str]:
        """Return an example configuration for this handler, with a text description.

        Example does not have to be a valid config, but should illustrate the main options.
        """
        example = HandlerConfig(
            name=cls.name,
            config={"file_path": "responses/{operation_id}-response.json"},
        )
        description = (
            "Saves the JSON response to the specified file path. "
            "The file_path option is required. file_path supports str.format replacement "
            "with tokens for operation_id, query_id, now, and any path, query or auth parameters."
        )
        return example, description

    @classmethod
    def validate_config(cls, config: HandlerConfig) -> None:
        if "file_path" not in config.config:
            raise InvalidHandlerError("file_path is required in handler config.")
        if not config.name.startswith("esi-link."):
            raise InvalidHandlerError(
                "Handler name must be in the 'esi-link.' namespace."
            )


class HandlerManager(HandlerManagerProtocol):
    """A simple handler manager implementation."""

    def __init__(self) -> None:
        self.handlers: dict[str, type[ResponseHandlerProtocol]] = {}

    def get_handler(self, config: HandlerConfig) -> ResponseHandlerProtocol:
        handler_cls = self.handlers.get(config.name)
        if not handler_cls:
            raise HandlerNotFoundError(f"Handler not found: {config.name}")
        return handler_cls.from_config(config)

    def register_handler(
        self, name: str, handler_cls: type[ResponseHandlerProtocol]
    ) -> None:
        if not issubclass(handler_cls, ResponseHandlerProtocol):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise InvalidHandlerError(
                f"Handler class must implement ResponseHandlerProtocol: {name}"
            )
        self.handlers[name] = handler_cls
