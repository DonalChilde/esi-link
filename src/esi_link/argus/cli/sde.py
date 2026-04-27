import typer
from eve_static_data.cli.main_typer import app as eve_static_data_app

from esi_link.argus.cli.import_sde import app as import_sde_app
from esi_link.cli.callback import default_options

app = typer.Typer(
    no_args_is_help=True,
    help="Commands for working with EVE Static Data Export (SDE) data in the Argus app.",
)
app.add_typer(import_sde_app)
app.add_typer(
    eve_static_data_app,
    name="esd",
    help="Commands for working with EVE static data.",
    callback=default_options,
)
