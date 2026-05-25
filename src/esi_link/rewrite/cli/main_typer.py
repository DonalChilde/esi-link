"""Main entry point for the Esi Link CLI using Typer."""

import typer

from esi_link.rewrite.cli.auth import app as auth_app
from esi_link.rewrite.cli.callback import default_options

app = typer.Typer(
    no_args_is_help=True,
    callback=default_options,
    help="Esi Link Command Line Interface.",
)
app.add_typer(auth_app, name="auth", help="Authentication-related commands.")
