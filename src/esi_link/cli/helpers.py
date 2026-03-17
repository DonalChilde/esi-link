"""Helper functions for the ESI Link CLI."""

from typing import cast

import typer

from esi_link.v3.settings import EsiLinkSettings


def get_settings_from_context(ctx: typer.Context):
    """Helper function to get the ESI Link settings from the Typer context."""
    if ctx.obj is None or "esi-link-settings" not in ctx.obj:
        raise ValueError("ESI Link settings not found in context.")
    return cast(EsiLinkSettings, ctx.obj["esi-link-settings"])
