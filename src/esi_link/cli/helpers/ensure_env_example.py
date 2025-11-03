"""Ensure that an example .esi-link.env file exists."""

from pathlib import Path

from esi_link.settings import env_example


def ensure_env_example(file_path: Path) -> bool:
    """Ensure that a file exists at the file_path.

    If no file exists, make an example .esi-link.env file.

    Args:
        file_path: The path to the file to check or create.

    Returns:
        True if the file already existed, False if it was created.
    """
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(env_example())
        return False
    return True
