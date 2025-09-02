from collections.abc import Callable

import typer


def filter_if_silent(is_silent: bool) -> Callable[[str], None]:
    """Filter messages based on silent mode."""

    def msg_filter(msg: str) -> None:
        if is_silent:
            return
        typer.echo(msg)

    return msg_filter
