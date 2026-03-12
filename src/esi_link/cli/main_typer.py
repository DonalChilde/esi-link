"""Main entry point for the Esi Link CLI using Typer."""

import logging

import typer

from esi_link import __app_name__, __version__
from esi_link.cli.cache import app as cache_app
from esi_link.cli.config_info import app as config_info_app
from esi_link.cli.esi_auth.main_typer import app as esi_auth_app
from esi_link.cli.esi_schema import app as esi_schema_app
from esi_link.logging_config import setup_logging
from esi_link.settings import get_settings

logger = logging.getLogger(__name__)
app = typer.Typer(no_args_is_help=True)
app.add_typer(
    esi_schema_app, name="schema", help="ESI schema information and management."
)
app.add_typer(cache_app, name="cache", help="ESI cache management commands.")
app.add_typer(
    esi_auth_app, name="auth", help="Commands for managing ESI authentication."
)
app.add_typer(config_info_app)


@app.callback(invoke_without_command=True)
def default_options(ctx: typer.Context):
    """Esi Link Command Line Interface.

    Insert pithy saying here
    """
    settings = get_settings()
    setup_logging(log_dir=settings.log_dir)
    ctx.obj = {"esi-link-settings": settings}
    logger.info(
        f"Starting {__app_name__} v{__version__} with settings: {settings.model_dump_json()}"
    )
