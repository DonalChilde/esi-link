import logging
from dataclasses import asdict
from pathlib import Path

from yaml import safe_dump

from esi_link.handlers.errors import (
    ResponseHandlerError,
)
from esi_link.handlers.response_group.helpers import (
    ResponseGroupSummary,
    make_response_group_summary,
)
from esi_link.handlers.response_group.templated_file_saver_abc import (
    GroupTemplatedFileSaverABC,
)
from esi_link.models_and_protocols import (
    ResponseGroup,
)

logger = logging.getLogger(__name__)


class ResponseGroupSummaryToFileHandler(GroupTemplatedFileSaverABC):
    """A summary of a ResponseGroup, containing performance metrics."""

    name = "esi-link:response_group_summary_to_file_handler"

    def __init__(
        self, output_dir: Path, filename_template: str, overwrite: bool = False
    ) -> None:
        super().__init__(output_dir, filename_template, overwrite)
        self.summary: ResponseGroupSummary | None = None

    async def handle_response_group(
        self, response_group: ResponseGroup
    ) -> ResponseGroup:
        """Handle the response group by creating a summary of it."""
        self.summary = make_response_group_summary(response_group)
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
            stats = safe_dump(asdict(self.summary), sort_keys=False)
            f.write(stats)
        return response_group
