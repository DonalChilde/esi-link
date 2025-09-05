import json
from time import perf_counter
from typing import Annotated
from uuid import uuid4

import typer

from esi_link.esi_client.esi_client import EsiClient
from esi_link.esi_client.esi_memory_cache import EsiMemoryCache
from esi_link.esi_client.link_cache_protocol import LinkCacheProtocol
from esi_link.esi_client.models import EsiQuery
from esi_link.esi_schema.eve_openapi import EveOpenApi
from esi_link.esi_schema.schema_store import SchemaStore

app = typer.Typer(no_args_is_help=True)


@app.command()
def get(
    ctx: typer.Context,
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
    start = perf_counter()
    typer.echo(f"Getting ESI data for operation ID: {operation_id}")

    # TODO use pydantic models for parameters
    # parse parameters
    path_dict = json.loads(path_parameters)
    query_dict = json.loads(query_parameters)
    header_dict = json.loads(header_parameters)
    if path_dict:
        typer.echo(f"Path parameters: {json.dumps(path_dict, indent=2)}")
    if query_dict:
        typer.echo(f"Query parameters: {json.dumps(query_dict, indent=2)}")
    if header_dict:
        typer.echo(f"Header parameters: {json.dumps(header_dict, indent=2)}")

    schema_store = ctx.obj.schema_store
    cache = EsiMemoryCache()
    client = get_client(schema_store, cache)
    esi_query = EsiQuery(
        query_id=uuid4(),
        operation_id=operation_id,
        path_parameters=path_dict,
        query_parameters=query_dict,
        headers=header_dict,
    )

    result = client.query(esi_query)
    typer.echo(json.dumps(json.loads(result.text), indent=2))

    typer.echo(f"Completed in {perf_counter() - start:.2f} seconds.")


def get_client(schema_store: SchemaStore, cache: LinkCacheProtocol):
    schema_api = EveOpenApi.from_schema_store(schema_store)
    client = EsiClient(
        schema_api=schema_api,
        cache=cache,
    )
    return client
