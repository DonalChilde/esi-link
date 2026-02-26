import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True, help="Commands related to the ESI schema.")


@app.command()
def status(ctx: typer.Context):
    """Show the status of the ESI schema."""
    console = Console()
    ...


@app.command()
def download(ctx: typer.Context):
    """Download the ESI schema."""
    console = Console()
    ...


def operations(ctx: typer.Context):
    """List the operations available in the ESI schema."""
    console = Console()
    ...
