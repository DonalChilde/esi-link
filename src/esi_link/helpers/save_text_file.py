"""Helper function to save text to a file, with optional overwrite behavior."""

from pathlib import Path


def save_text_file(
    *, text: str, output_dir: Path, file_name: str, overwrite: bool = False
) -> Path:
    """Save text to a file, optionally overwriting if it exists.

    Args:
        text: The text to save to the file.
        output_dir: The directory to save the file in.
        file_name: The name of the file to save.
        overwrite: Whether to overwrite the file if it already exists. Defaults to False.

    Returns:
        The path to the saved file.

    Raises:
        FileExistsError: If the file already exists and overwrite is False.
    """
    output_file = output_dir / file_name
    if overwrite:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as f:
            f.write(text)
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("x", encoding="utf-8") as f:
            f.write(text)
    return output_file
