import json
from typing import Annotated

import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def get(
    operation_id: Annotated[
        str, typer.Argument(help="The operation ID to execute.")
    ] = "GetStatus",
    path_parameters: Annotated[
        str,
        typer.Option(
            "-p, --path", help="Path parameters for the operation.", show_default=False
        ),
    ] = "{}",
    query_parameters: Annotated[
        str,
        typer.Option(
            "-q, --query",
            help="Query parameters for the operation.",
            show_default=False,
        ),
    ] = "{}",
    header_parameters: Annotated[
        str,
        typer.Option(
            "-h, --header",
            help="Header parameters for the operation.",
            show_default=False,
        ),
    ] = "{}",
):
    """Get ESI data."""
    typer.echo(f"Getting ESI data for operation ID: {operation_id}")
    if path_parameters:
        typer.echo(f"Path parameters: {path_parameters}")
    if query_parameters:
        typer.echo(f"Query parameters: {query_parameters}")
    if header_parameters:
        typer.echo(f"Header parameters: {header_parameters}")

    # TODO use pydantic models for parameters
    # parse parameters
    path_dict = json.loads(path_parameters)
    query_dict = json.loads(query_parameters)
    header_dict = json.loads(header_parameters)

    # instantiate required objects
    # validate parameters
    # make request
    # return data
