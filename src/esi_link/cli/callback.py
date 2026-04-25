"""Callback functions for the ESI Link CLI."""

import logging
from dataclasses import asdict

import typer
from eve_static_data.settings import get_settings as get_esd_settings

from esi_link import __app_name__, __version__
from esi_link.argus.settings import ArgusSettings
from esi_link.logging_config import setup_logging
from esi_link.settings import get_settings

logger = logging.getLogger(__name__)


def default_options(ctx: typer.Context):
    """Esi Link Command Line Interface.

    Insert pithy saying here
    """
    settings = get_settings()
    setup_logging(log_dir=settings.log_directory)
    ctx.obj = {"esi-link-settings": settings}
    # Make an argus-settings field for now, this can be removed when Argus is split from ESI Link and has its own app.

    esd_settings = get_esd_settings()
    esd_settings.application_directory = (
        settings.application_directory / "argus" / "eve-static-data"
    )

    # When Argus is split, esd_settings will be set from the ArgusSettings dataclass
    ctx.obj["esd-settings"] = esd_settings
    argus_settings = ArgusSettings(
        application_directory=settings.application_directory / "argus",
        sde_directory=settings.application_directory / "argus" / "sde",
        esi_link_settings=settings,
        esd_settings=esd_settings,
    )
    ctx.obj["argus-settings"] = argus_settings
    logger.info(
        f"Starting {__app_name__} v{__version__} with settings: {asdict(settings)!r}"
    )
