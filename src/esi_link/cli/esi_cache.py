import typer
from rich import print as rich_print

app = typer.Typer(no_args_is_help=True)


@app.command()
def clear(ctx: typer.Context):
    """Clear the ESI cache file."""
    with ctx.obj.cache as cache:
        cache.clear()
    typer.echo("ESI cache cleared.")


@app.command()
def stats(ctx: typer.Context):
    """Show statistics about the ESI cache."""
    with ctx.obj.cache as cache:
        stats = cache.stats()
    typer.echo("ESI Cache Statistics:")
    rich_print(stats)
