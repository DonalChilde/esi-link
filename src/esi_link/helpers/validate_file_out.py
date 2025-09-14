####################################################
#                                                  #
#    src/snippets/file/validate_file_out.py
#                                                  #
####################################################
# Created by: Chad Lowe                            #
# Created on: 2022-10-29T09:11:28-07:00            #
# Last Modified: 2023-04-17T14:36:01.591231+00:00  #
# Source: https://github.com/DonalChilde/snippets  #
####################################################
from pathlib import Path


def validate_file_out(
    file_path: Path, *, overwrite: bool = False, ensure_parent: bool = True
) -> bool:
    """Ensure that a path is suitable for file output.

    Optionally can ensure that parent directories exist.
    """
    if file_path.is_dir():
        raise ValueError(
            f"file_path is an invalid destination. It is an existing directory."
            f"file_path = {file_path}"
        )
    if not overwrite and file_path.is_file():
        raise ValueError(
            f"file_path is an invalid destination. "
            "It is an existing file and overwrite was not selected."
            f"file_path = {file_path}"
        )
    if ensure_parent:
        parent = file_path.parent
        parent.mkdir(parents=True, exist_ok=True)
    if not file_path.parent.is_dir():
        raise ValueError(
            f"file_path is an invalid destination. "
            "It's parent directory is not a directory, or it doesn't exist."
            f"file_path = {file_path}"
        )
    return True
