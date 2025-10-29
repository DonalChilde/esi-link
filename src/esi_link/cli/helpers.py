from collections.abc import Callable
from pathlib import Path

import typer

from esi_link.settings import env_example


def filter_if_silent(is_silent: bool) -> Callable[[str], None]:
    """Filter messages based on silent mode."""

    def msg_filter(msg: str) -> None:
        if is_silent:
            return
        typer.echo(msg)

    return msg_filter


def ensure_env_example(file_path: Path) -> bool:
    """Ensure that a file exists at the file_path.

    If no file exists, make an example .env file.

    Args:
        file_path: The path to the file to check or create.

    Returns:
        True if the file was created, False if it already existed.
    """
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(env_example())
        return False
    return True
