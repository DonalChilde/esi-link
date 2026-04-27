"""Commands for working with Esi Argus data."""

import typer

from esi_link.cli.callback import default_options

from .character import app as character_app
from .corporation import app as corporation_app
from .industry import app as industry_app
from .market import app as market_app
from .sde import app as sde_app

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
app.add_typer(
    industry_app, name="industry", help="Commands for working with industry data."
)
app.add_typer(
    sde_app,
    name="sde",
    help="Commands for working with EVE Static Data Export (SDE) data.",
)
# esd cli commands are used by the argus cli commands, so we add them as a subcommand here
# update the call back to use the default options for the argus cli commands, where the esd
# settings are stored in the context object
