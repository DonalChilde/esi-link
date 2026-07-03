"""Write UTF-8 text files with explicit overwrite semantics."""

from pathlib import Path


def save_text_file(
    *, text: str, output_directory: Path, file_name: str, overwrite: bool = False
) -> Path:
    """Write text to ``output_directory / file_name``.

    Args:
        text: Text content to write.
        output_directory: Directory to write the file into.
        file_name: Output file name.
        overwrite: If true, replace existing file contents. If false, fail when
            the file already exists.

    Returns:
        Path to the written file.

    Raises:
        FileExistsError: If the target file exists and ``overwrite`` is false.

    Notes:
        Parent directories are created automatically when missing.
    """
    output_file = output_directory / file_name
    if overwrite:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as f:
            f.write(text)
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("x", encoding="utf-8") as f:
            f.write(text)
    return output_file
