"""Main entry point for the Esi Link CLI using Typer."""

import logging

import typer

from esi_link.cli.argus import app as argus_app
from esi_link.cli.cache import app as cache_app
from esi_link.cli.callback import default_options
from esi_link.cli.config_info import app as config_info_app
from esi_link.cli.esi_auth.main_typer import app as esi_auth_app
from esi_link.cli.esi_schema import app as esi_schema_app
from esi_link.cli.examples import app as examples_app
from esi_link.cli.requests import app as requests_app

logger = logging.getLogger(__name__)
app = typer.Typer(
    no_args_is_help=True,
    callback=default_options,
    help="Esi Link Command Line Interface.",
)
app.add_typer(
    esi_schema_app, name="schema", help="ESI schema information and management."
)
app.add_typer(cache_app, name="cache", help="ESI cache management commands.")
app.add_typer(
    esi_auth_app, name="auth", help="Commands for managing ESI authentication."
)
# Add config info commands to the main app as indiviual commands, rather than a subcommand
app.add_typer(config_info_app)
app.add_typer(
    examples_app, name="examples", help="Commands for demonstrating ESI Link requests."
)
app.add_typer(
    requests_app, name="requests", help="Commands for managing ESI Link requests."
)
app.add_typer(
    argus_app, name="argus", help="Commands for working with ESI Link Argus data."
)
