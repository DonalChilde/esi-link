"""Helper functions for the Argus CLI commands."""

from typing import cast

import typer

from esi_link.argus.settings import ArgusSettings


def get_argus_settings_from_context(ctx: typer.Context) -> ArgusSettings:
    """Helper function to get the Argus settings from the Typer context."""
    if ctx.obj is None or "argus-settings" not in ctx.obj:
        raise ValueError("Argus settings not found in context.")
    return cast(ArgusSettings, ctx.obj["argus-settings"])
