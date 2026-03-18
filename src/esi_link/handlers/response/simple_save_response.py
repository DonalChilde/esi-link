"""A response handler that saves the response to disk as a JSON file."""

import logging
from pathlib import Path
from typing import Self

from esi_link.handlers.errors import HandlerCreationError, HandlerValidationError
from esi_link.handlers.response.handler_abc import ResponseHandlerABC
from esi_link.handlers.response.helpers import check_required_keys
from esi_link.helpers.save_text_file import save_text_file
from esi_link.models_and_protocols import (
    Response,
    ResponseHandlerConfig,
)

logger = logging.getLogger(__name__)


class SimpleSaveToDiskResponseHandler(ResponseHandlerABC):
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
        self.output_file: Path | None = None

    @staticmethod
    def _check_directory(output_dir: str) -> Path:
        """Check if the output directory is valid."""
        if output_dir.startswith("/"):
            home_dir = str(Path.home())
            if not output_dir.startswith(home_dir):
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
        self.output_file = file_path
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
        ```
        # json
        {
            "name": "esi-link:simple_save_to_disk",
            "config": {"output_dir": "~/path/to/output/dir", "overwrite": false},
        }
        ```
        """
        try:
            output_dir = cls._check_directory(config.config["output_dir"])
            overwrite = config.config["overwrite"]
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
