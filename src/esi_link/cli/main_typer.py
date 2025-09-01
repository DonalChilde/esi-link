"""Command-line interface."""

from time import perf_counter_ns
from typing import Annotated

import typer

from esi_link import CONFIG


def default_options(
    ctx: typer.Context,
    debug: Annotated[bool, typer.Option(help="Enable debug output.")] = False,
    verbosity: Annotated[int, typer.Option("-v", help="Verbosity.", count=True)] = 1,
):
    """Esi Link Command Line Interface.

    Insert pithy saying here
    """
    ctx.ensure_object(dict)
    ctx.obj["START_TIME"] = perf_counter_ns()
    ctx.obj["DEBUG"] = debug
    ctx.obj["VERBOSITY"] = verbosity

    if ctx.obj["VERBOSITY"] > 1:
        typer.echo("App configuration:")
        typer.echo(f"{debug=}")
        typer.echo(f"{verbosity=}")
        typer.echo(f"{CONFIG=!r}")


app = typer.Typer(callback=default_options)


if __name__ == "__main__":
    app()
