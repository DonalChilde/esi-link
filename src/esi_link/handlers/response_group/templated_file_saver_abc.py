"""Standard File Saver Response Handler for ESI Link."""

import logging
from abc import abstractmethod
from pathlib import Path
from string import Template
from typing import Self

from whenever import Instant

from esi_link.handlers.errors import (
    HandlerBadResponseError,
    HandlerCreationError,
    HandlerValidationError,
)
from esi_link.handlers.response_group.group_handler_abc import ResponseGroupHandlerABC
from esi_link.helpers.file_safe_string import file_safe_string
from esi_link.models_and_protocols import (
    ResponseGroup,
    ResponseGroupHandlerConfig,
)

logger = logging.getLogger(__name__)


class TemplatedFileSaverABC(ResponseGroupHandlerABC):
    """ResponseGroup Handler that saves data to a templated file path.

    ABC for saving response_group data to a templated filename.

    If there are any errors in the response_group (network exceptions, http response is None, etc),
    the file name will still be generated from the template, but will have the
    suffix "_WITH_ERRORS" added to it, before the file extension.

    override handle_response_group to implement specific behavior.
    """

    name = "esi-link:group_templated_file_saver_abc"

    def __init__(
        self, output_dir: Path, filename_template: str, overwrite: bool = False
    ) -> None:
        """ResponseGroup Handler that saves the response to a templated file path."""
        self.output_dir = output_dir
        self.filename_template = filename_template
        self.overwrite = overwrite

    def _get_tokens(self, response_group: ResponseGroup) -> dict[str, str]:
        """Get the tokens for the filename template from the response group."""
        return tokens_from_response_group(response_group)

    def _has_errors(self, response_group: ResponseGroup) -> bool:
        """Check if the response_group has errors."""
        for response in response_group.responses.values():
            if response.http_response is None or response.network_exception_messages:
                return True
        return False

    def _get_filename(self, response_group: ResponseGroup) -> Path:
        """Get the filename for the response by filling in the template."""
        tokens = self._get_tokens(response_group)
        filename_str = Template(self.filename_template).safe_substitute(tokens)
        filename = Path(filename_str)
        if self._has_errors(response_group):
            filename = filename.with_stem(filename.stem + "_WITH_ERRORS")
        return filename

    def get_output_path(self, response_group: ResponseGroup) -> Path:
        """Get the full output path for the response."""
        filename = self._get_filename(response_group)
        output_path = self.output_dir / filename
        # check that the output path is within the output directory to prevent directory traversal attacks
        if not output_path.resolve().is_relative_to(self.output_dir.resolve()):
            raise HandlerBadResponseError(
                "Output path is outside of output directory. Possible directory traversal attack.",
                response_data={
                    "request_group_id": str(response_group.request_group.group_id),
                    "output_path": str(output_path),
                    "output_dir": str(self.output_dir),
                },
            )
        return output_path

    @classmethod
    def from_config(cls, config: ResponseGroupHandlerConfig) -> Self:
        """Create a TemplatedFileSaverResponseHandler from a ResponseGroupHandlerConfig."""
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
    def validate_config(cls, config: ResponseGroupHandlerConfig) -> None:
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


def tokens_from_response_group(response_group: ResponseGroup) -> dict[str, str]:
    """Get the tokens for the filename template from the response_group."""
    request_group_id = str(response_group.request_group.group_id)
    first_response = next(iter(response_group.responses.values()), None)

    response_date = (
        first_response.http_response.date
        if first_response and first_response.http_response
        else None
    )
    try:
        iso_response_date = (
            Instant.parse_rfc2822(response_date).format_iso()
            if response_date
            else "NO_RESPONSE_DATE"
        )
    except Exception:
        iso_response_date = "NO_RESPONSE_DATE"

    token_dict = {
        "request_group_id": request_group_id,
        "response_date": response_date if response_date else "NO_RESPONSE_DATE",
        "iso_response_date": iso_response_date,
    }

    # ensure each value is a file-safe string
    token_dict = {k: file_safe_string(v) for k, v in token_dict.items()}

    # Empty tokens can cause issues with filename templates, so replace any empty
    # tokens with "EMPTY_TOKEN"
    token_dict = {k: (v if v else "EMPTY_TOKEN") for k, v in token_dict.items()}
    return token_dict
