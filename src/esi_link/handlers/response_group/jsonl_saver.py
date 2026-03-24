"""ResponseGroup Handler that saves data to a templated file path as jsonl."""

import json
from pathlib import Path

from esi_link.handlers.errors import ResponseHandlerError
from esi_link.handlers.response.helpers import make_response_details
from esi_link.handlers.response_group.templated_file_saver_abc import (
    TemplatedFileSaverABC,
)
from esi_link.models_and_protocols import ResponseGroup


class JsonlGroupSaver(TemplatedFileSaverABC):
    """ResponseGroup Handler that saves data to a templated file path as jsonl.

    If there are any errors in the response_group (network exceptions, http response is None, etc),
    the file name will still be generated from the template, but will have the
    suffix "_WITH_ERRORS" added to it, before the file extension.

    This handler saves each response in the response group as a separate line in a jsonl file.
    Each line is a json object with the following keys:
    - All the fields from the original Request, plus the following additional fields:
    - response_data: the data from the http response, if available, otherwise None
    - response_date: the date of the http response, if available, otherwise "NO_RESPONSE_DATE"
    """

    name = "esi-link:jsonl_group_saver"

    def __init__(
        self, output_dir: Path, filename_template: str, overwrite: bool = False
    ) -> None:
        """ResponseGroup Handler that saves the response group to a templated file path as jsonl."""
        super().__init__(output_dir, filename_template, overwrite)
        self.file_path: Path | None = None

    async def handle_response_group(
        self, response_group: ResponseGroup
    ) -> ResponseGroup:
        """Handle the response group by saving each response as a line in a jsonl file."""
        output_path = self.get_output_path(response_group)
        if output_path.is_dir():
            raise ResponseHandlerError(
                f"Output path {output_path} is a directory, expected a file path."
            )
        if output_path.exists() and not self.overwrite:
            raise ResponseHandlerError(
                f"File {output_path} already exists and overwrite is set to False."
            )
        self.file_path = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for response in response_group.responses.values():
                response_details = make_response_details(response)
                f.write(f"{json.dumps(response_details)}\n")
        return response_group
