import typer

app = typer.Typer(no_args_is_help=True)

from esi_link.esi_client.esi_file_cache import EsiFileCache


@app.command()
def clear(ctx: typer.Context):
    """Clear the ESI cache file."""

    ctx.obj.cache.clear()
    typer.echo("ESI cache cleared.")
