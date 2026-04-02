"""Commands for working with Esi Argus data."""

import typer

from .character import app as character_app
from .corporation import app as corporation_app
from .market import app as market_app

app = typer.Typer(no_args_is_help=True, help="Commands for working with Esi data.")
app.add_typer(
    character_app, name="character", help="Commands for working with character data."
)
app.add_typer(
    corporation_app,
    name="corporation",
    help="Commands for working with corporation data.",
)
app.add_typer(market_app, name="market", help="Commands for working with market data.")
