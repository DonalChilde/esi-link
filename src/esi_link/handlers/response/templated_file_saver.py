import logging
from pathlib import Path
from string import Template, ascii_letters, digits
from typing import Self

from esi_link.handlers.errors import (
    HandlerBadResponseError,
    HandlerCreationError,
    HandlerValidationError,
)
from esi_link.handlers.response.handler_abc import ResponseHandlerABC
from esi_link.helpers.save_text_file import save_text_file
from esi_link.models_and_protocols import (
    Response,
    ResponseHandlerConfig,
)

logger = logging.getLogger(__name__)


class TemplatedFileSaverResponseHandler(ResponseHandlerABC):
    """Response Handler that saves the response to a templated file path."""

    name = "esi-link:templated_response_saver"

    def __init__(
        self, output_dir: Path, filename_template: str, overwrite: bool = False
    ) -> None:
        self.output_dir = output_dir
        self.filename_template = filename_template
        self.overwrite = overwrite

    async def __call__(self, response: Response) -> Response:
        """Handle the response by saving it to a templated file path."""
        output_file_path = self.get_output_path(response)
        text_to_save = self.get_text_to_save(response)
        self.save_file(output_file_path, text_to_save)
        return response

    def _get_tokens(self, response: Response) -> dict[str, str]:
        """Get the tokens for the filename template from the response."""
        return tokens_from_response(response)

    def _has_errors(self, response: Response) -> bool:
        """Check if the response has errors.

        Checks for:
        - presence of exception messages in the response
        - http response is None
        """
        if response.exception_messages:
            return True
        if response.http_response is None:
            return True
        return False

    def _get_filename(self, response: Response) -> Path:
        """Get the filename for the response by filling in the template."""
        tokens = self._get_tokens(response)
        filename_str = Template(self.filename_template).safe_substitute(tokens)
        filename = Path(filename_str)
        if self._has_errors(response):
            filename = filename.with_stem(filename.stem + "_WITH_ERRORS")
        return filename

    def get_output_path(self, response: Response) -> Path:
        """Get the full output path for the response."""
        filename = self._get_filename(response)
        output_path = self.output_dir / filename
        # check that the output path is within the output directory to prevent directory traversal attacks
        if not output_path.resolve().is_relative_to(self.output_dir.resolve()):
            raise HandlerBadResponseError(
                "Output path is outside of output directory. Possible directory traversal attack.",
                response_data={
                    "request_id": str(response.request.request_id),
                    "output_path": str(output_path),
                    "output_dir": str(self.output_dir),
                },
            )
        return output_path

    def get_text_to_save(self, response: Response) -> str:
        """Get the text to save to the file for the response.

        Returns the http response body text if there are no errors.

        If the response has errors, returns the full response as a JSON string instead,
        since the http response body may not be present or may not contain useful information
        in the case of an error.
        """
        if self._has_errors(response):
            return response.model_dump_json(indent=2)
        else:
            assert response.http_response is not None  # for type checker
            return response.http_response.body_text

    def save_file(self, output_file_path: Path, text_to_save: str) -> None:
        """Save the text to the file at the output path."""
        output_dir = output_file_path.parent
        file_name = output_file_path.name
        try:
            save_text_file(
                text=text_to_save,
                output_dir=output_dir,
                file_name=file_name,
                overwrite=self.overwrite,
            )
        except Exception as e:
            raise HandlerBadResponseError(
                "Failed to save file for response.",
                response_data={
                    "request_id": str(output_file_path),
                    "exception_message": str(e),
                },
            ) from e

    @classmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        """Create a TemplatedFileSaverResponseHandler from a ResponseHandlerConfig."""
        try:
            cls.validate_config(config)
            return cls(
                output_dir=Path(config.config["output_dir"]),
                filename_template=config.config["filename_template"],
                overwrite=config.config["overwrite"],
            )
        except HandlerValidationError as e:
            raise HandlerCreationError(
                f"Invalid config for TemplatedFileSaverResponseHandler. {e}",
            ) from e
        except KeyError as e:
            raise HandlerCreationError(
                f"Missing required config key for TemplatedFileSaverResponseHandler: {e}",
            ) from e
        except Exception as e:
            raise HandlerCreationError(
                f"Failed to create TemplatedFileSaverResponseHandler from config. {e}",
            ) from e

    @classmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        """Validate the ResponseHandlerConfig for TemplatedFileSaverResponseHandler."""
        required_keys = {"output_dir", "filename_template", "overwrite"}
        cls._check_available_keys(config, required_keys)
        if not isinstance(config.config["output_dir"], str):
            raise HandlerValidationError(
                "output_dir must be a string.", config=config.model_dump(mode="json")
            )
        if not isinstance(config.config["filename_template"], str):
            raise HandlerValidationError(
                "filename_template must be a string.",
                config=config.model_dump(mode="json"),
            )
        if not isinstance(config.config["overwrite"], bool):
            raise HandlerValidationError(
                "overwrite must be a boolean.", config=config.model_dump(mode="json")
            )


def tokens_from_response(response: Response) -> dict[str, str]:
    """Get the tokens for the filename template from the response."""
    request_id = str(response.request.request_id)
    operation_id = response.request.operation_id or "NO_OPERATION_ID"
    response_date = response.http_response.date if response.http_response else None
    path_params = {
        f"param_{k}": str(v) for k, v in response.request.path_parameters.items()
    }
    query_params = {
        f"param_{k}": str(v) for k, v in response.request.query_parameters.items()
    }
    token_dict = {
        "request_id": request_id,
        "operation_id": operation_id,
        "response_date": response_date if response_date else "NO_RESPONSE_DATE",
    }
    token_dict.update(path_params)
    token_dict.update(query_params)
    # ensure each value is a file-safe string
    token_dict = {k: file_safe_string(v) for k, v in token_dict.items()}

    # Empty tokens can cause issues with filename templates, so replace any empty
    # tokens with "EMPTY_TOKEN"
    token_dict = {k: (v if v else "EMPTY_TOKEN") for k, v in token_dict.items()}
    return token_dict


def file_safe_string(s: str) -> str:
    """Convert a string to a file-safe string.

    Converts a string to a file-safe string by:
    - replacing non-alphanumeric characters with underscores.
    - collapsing multiple consecutive underscores into a single underscore.
    - removing leading and trailing underscores.

    """
    replaced = "".join(c if is_alphanum_or_dash_character(c) else "_" for c in s)
    collapsed = "_".join(part for part in replaced.split("_") if part)
    trimmed = collapsed.strip("_")
    return trimmed


allowed_chars = set(ascii_letters + digits + "-" + "_")


def is_alphanum_or_dash(s: str) -> bool:
    """Check if a string is alphanumeric or contains dashes or underscores."""
    return all(is_alphanum_or_dash_character(c) for c in s)


def is_alphanum_or_dash_character(c: str) -> bool:
    """Check if a character is alphanumeric or a dash or underscore."""
    return c in allowed_chars
