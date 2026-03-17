import typer
from rich.console import Console

from esi_link.v3.models import Request, RequestGroup

app = typer.Typer(
    no_args_is_help=True, help="Commands for testing ESI Link functionality."
)


@app.command()
def test(ctx: typer.Context):
    """Run tests for ESI Link."""
    console = Console()
    console.print("Running tests...")
    # TODO implement tests
    console.print("Tests completed.")
