"""Authentication-related CLI commands."""

import typer

from esi_link.rewrite.cli.auth.add_token import app as add_token_app
from esi_link.rewrite.cli.auth.init_store import app as init_store_app

app = typer.Typer(no_args_is_help=True)

app.add_typer(init_store_app, help="Initialize the authentication store.")
app.add_typer(add_token_app, help="Add a token for a character.")
