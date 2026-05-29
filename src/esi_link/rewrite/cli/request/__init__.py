import typer

from esi_link.rewrite.cli.request.execute import app as execute_app
from esi_link.rewrite.cli.request.samples import app as samples_app

app = typer.Typer(no_args_is_help=True)

app.add_typer(samples_app, help="Commands for saving example requests to disk.")
app.add_typer(execute_app, help="Commands for executing requests from JSON files.")
