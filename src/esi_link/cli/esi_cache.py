"""CLI commands for ESI cache management."""

# FIXME: Implement cache statistics and clearing functionality

import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def clear(ctx: typer.Context):
    """Clear the ESI cache file."""
    raise NotImplementedError("Cache clearing not yet implemented.")


@app.command()
def stats(ctx: typer.Context):
    """Show statistics about the ESI cache."""
    raise NotImplementedError("Cache statistics not yet implemented.")
