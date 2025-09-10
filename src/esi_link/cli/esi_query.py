import json
from time import perf_counter
from typing import Annotated
from uuid import uuid4

import typer

from esi_link.esi_client.esi_client import EsiClient
from esi_link.esi_client.esi_memory_cache import EsiMemoryCache
from esi_link.esi_client.models import EsiQuery
from esi_link.esi_schema.eve_openapi import EveOpenApi

app = typer.Typer(no_args_is_help=True)


@app.command()
def get(
    ctx: typer.Context,
    operation_id: Annotated[
        str, typer.Argument(help="The operation ID to execute.")
    ] = "GetStatus",
    parameters: Annotated[
        list[str],
        typer.Option("-p", "--parameter", help="Parameters as key=value strings."),
    ] = [],
):
    """Get ESI data.

    Example:
        esi-link query get GetMarketsRegionIdHistory -p region_id=10000002 -p type_id=34
    """

    start = perf_counter()
    typer.echo(f"Getting ESI data for operation ID: {operation_id}")
    client = init_client(ctx)

    # TODO use pydantic models for parameters?

    # split input parameters into key, value pairs
    # will ignore any that don't have an '=', or have more than one '='
    params_dict = {
        x[0]: x[1] for x in (y.split("=", 1) for y in parameters) if len(x) == 2
    }
    split_params = client.split_request_parameters(operation_id, params_dict)

    # This will be debug print only -> when implemented
    if len(parameters) != (
        len(split_params.path)
        + len(split_params.query)
        + len(split_params.header)
        + len(split_params.unknown)
    ):
        typer.echo(
            f"Warning: Some parameters were not recognized and will be ignored. {parameters!r}"
        )
    if split_params.path:
        typer.echo(f"Path parameters: {json.dumps(split_params.path, indent=2)}")
    if split_params.query:
        typer.echo(f"Query parameters: {json.dumps(split_params.query, indent=2)}")
    if split_params.header:
        typer.echo(f"Header parameters: {json.dumps(split_params.header, indent=2)}")
    if split_params.unknown:
        typer.echo(f"Unknown parameters: {json.dumps(split_params.unknown, indent=2)}")

    esi_query = EsiQuery(
        query_id=uuid4(),
        operation_id=operation_id,
        path_parameters=split_params.path,
        query_parameters=split_params.query,
        headers=split_params.header,
    )
    client.validate_query(esi_query)

    result = client.query(esi_query)
    typer.echo(json.dumps(json.loads(result.text), indent=2))

    typer.echo(f"Completed in {perf_counter() - start:.2f} seconds.")


def init_client(ctx: typer.Context) -> EsiClient:
    schema_store = ctx.obj.schema_store
    # TODO use real cache.
    cache = EsiMemoryCache()
    schema_api = EveOpenApi.from_schema_store(schema_store)
    client = EsiClient(
        schema_api=schema_api,
        cache=cache,
    )
    return client
