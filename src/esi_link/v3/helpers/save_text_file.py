"""Helper function to save text to a file, with optional overwrite behavior."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def save_text_file(
    text: str, output_path: Path, file_name: str, overwrite: bool = False
) -> Path:
    """Save text to a file, optionally overwriting if it exists."""
    output_file = output_path / file_name
    if output_file.exists() and not overwrite:
        logger.warning(
            f"File {output_file} already exists and overwrite is False. Skipping."
        )
        raise FileExistsError(
            f"File {output_file} already exists and overwrite is False."
        )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(text)
    logger.info(f"Saved text file to {output_file}")
    return output_file
