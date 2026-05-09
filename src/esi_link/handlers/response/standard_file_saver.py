# """Standard File Saver Response Handler for ESI Link."""

# import logging
# from pathlib import Path
# from typing import Self

# from esi_link.handlers.errors import (
#     HandlerCreationError,
#     HandlerValidationError,
# )
# from esi_link.handlers.response.templated_file_saver_abc import TemplatedFileSaverABC
# from esi_link.models_and_protocols import (
#     Response,
#     ResponseHandlerConfig,
# )

# logger = logging.getLogger(__name__)


# class StandardFileSaverResponseHandler(TemplatedFileSaverABC):
#     """Response Handler that saves the response to a templated file path.

#     Saves the http response body text to a file at the output path generated from the
#     template.

#     If there are any errors in the response (network exceptions, http response is None, etc),
#     then saves the entire response as json instead, to capture the error information. In
#     this case, the file name will still be generated from the template, but will have the
#     suffix "_WITH_ERRORS" added to it, before the file extension.
#     """

#     name = "esi-link:standard_file_saver"

#     def __init__(
#         self, output_dir: Path, filename_template: str, overwrite: bool = False
#     ) -> None:
#         """Response Handler that saves the response to a templated file path."""
#         self.output_dir = output_dir
#         self.filename_template = filename_template
#         self.overwrite = overwrite

#     def get_text_to_save(self, response: Response) -> str:
#         """Get the text to save to the file for the response.

#         Returns the http response body text if there are no errors.

#         If the response has errors, returns the full response as a JSON string instead,
#         since the http response body may not be present or may not contain useful information
#         in the case of an error.
#         """
#         if self._has_errors(response):
#             return response.model_dump_json(indent=2)
#         else:
#             assert response.http_response is not None  # for type checker
#             return response.http_response.body_text

#     @classmethod
#     def from_config(cls, config: ResponseHandlerConfig) -> Self:
#         """Create a StandardFileSaverResponseHandler from a ResponseHandlerConfig."""
#         try:
#             cls.validate_config(config)
#             return cls(
#                 output_dir=Path(config.config["output_dir"]),
#                 filename_template=config.config["filename_template"],
#                 overwrite=config.config["overwrite"],
#             )
#         except HandlerValidationError as e:
#             raise HandlerCreationError(
#                 f"Invalid config for TemplatedFileSaverResponseHandler. {e}",
#             ) from e
#         except KeyError as e:
#             raise HandlerCreationError(
#                 f"Missing required config key for TemplatedFileSaverResponseHandler: {e}",
#             ) from e
#         except Exception as e:
#             raise HandlerCreationError(
#                 f"Failed to create TemplatedFileSaverResponseHandler from config. {e}",
#             ) from e

#     @classmethod
#     def validate_config(cls, config: ResponseHandlerConfig) -> None:
#         """Validate the ResponseHandlerConfig for TemplatedFileSaverResponseHandler."""
#         required_keys = {"output_dir", "filename_template", "overwrite"}
#         cls._check_available_keys(config, required_keys)
#         if not isinstance(config.config["output_dir"], str):
#             raise HandlerValidationError(
#                 "output_dir must be a string.", config=config.model_dump(mode="json")
#             )
#         if not isinstance(config.config["filename_template"], str):
#             raise HandlerValidationError(
#                 "filename_template must be a string.",
#                 config=config.model_dump(mode="json"),
#             )
#         if not isinstance(config.config["overwrite"], bool):
#             raise HandlerValidationError(
#                 "overwrite must be a boolean.", config=config.model_dump(mode="json")
#             )
