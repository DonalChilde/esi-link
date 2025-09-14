import json
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any
from uuid import uuid4

import typer

from esi_link.esi_client.esi_client import EsiClient
from esi_link.esi_client.esi_memory_cache import EsiMemoryCache
from esi_link.esi_client.models import EsiQuery
from esi_link.esi_schema.esi_api import EsiApi
from esi_link.esi_schema.esi_api_protocol import SplitParameters
from esi_link.helpers.csv import write_dicts_to_csv
from esi_link.helpers.response_to_json import response_to_json
from esi_link.helpers.validate_file_out import validate_file_out

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
    csv_data: Annotated[
        Path | None, typer.Option(help="Path to save the query response as CSV.")
    ] = None,
    json_data: Annotated[
        Path | None, typer.Option(help="Path to save the query response as JSON.")
    ] = None,
    json_query: Annotated[
        Path | None,
        typer.Option(help="Path to save the completed but unprocessed query as JSON."),
    ] = None,
    console: Annotated[
        bool, typer.Option(help="Print the query response as JSON to console.")
    ] = True,
    console_query: Annotated[
        bool, typer.Option(help="Print the completed but unprocessed query to console.")
    ] = False,
    json_indent: Annotated[int, typer.Option(help="Indent level for JSON output.")] = 2,
    file_overwrite: Annotated[
        bool, typer.Option(help="Allow overwriting existing files.")
    ] = False,
):
    """Get ESI data.

    Example:
        esi-link query get GetMarketsRegionIdHistory -p region_id=10000002 -p type_id=34
    """

    start = perf_counter()
    typer.echo(f"Getting ESI data for operation ID: {operation_id}")
    client = init_client(ctx)
    # split input parameters into key, value pairs
    params_list = parse_params(parameters)
    split_parameters = client.split_request_parameters(operation_id, params_list)
    if split_parameters.unknown:
        typer.echo(
            f"Warning: Some parameters were not recognized and will be ignored. {split_parameters.unknown!r}"
        )
    if len(parameters) != split_parameters.count():
        typer.echo(
            f"Warning: The count of input parameters does not match the split parameters. Were some parameter names repeated? {parameters!r}"
        )
    debug_print_split_parameters(ctx, parameters, split_parameters)
    esi_query = EsiQuery(
        query_id=uuid4(),
        operation_id=operation_id,
        path_parameters=split_parameters.path,
        query_parameters=split_parameters.query,
        headers=split_parameters.header,
    )
    client.validate_query(esi_query)
    client.query(esi_query)
    if esi_query.response is None:
        typer.echo("No response received for query. See logs for details.")
        raise typer.Exit(code=1)
    jsoned_response = response_to_json(esi_query.response)
    if csv_data:
        if isinstance(jsoned_response, list) and all(
            isinstance(item, dict) for item in jsoned_response
        ):
            save_csv(jsoned_response, csv_data, file_overwrite)
        elif isinstance(jsoned_response, dict):
            save_csv([jsoned_response], csv_data, file_overwrite)
        else:
            typer.echo(
                "Response data is not a list of dictionaries or a single dictionary. Cannot save as CSV."
            )
    if json_data:
        save_json(jsoned_response, json_data, file_overwrite, json_indent)
    if json_query:
        save_json_query(esi_query, json_query, file_overwrite, json_indent)
    if console_query:
        typer.echo(EsiQuery.model_dump_json(esi_query, indent=json_indent))
    if console:
        # print_json(data=jsoned_response, indent=json_indent)
        typer.echo(json.dumps(jsoned_response, indent=2))
    # print_json(data=jsoned_response)
    # print_json(EsiQuery.model_dump_json(esi_query))
    # typer.echo(json.dumps(jsoned_response, indent=2))

    typer.echo(f"Completed in {perf_counter() - start:.2f} seconds.")


def save_csv(data: list[dict[str, Any]], path: Path, overwrite: bool) -> None:
    """Save data as CSV to the given path."""
    if not data:
        typer.echo("No data to save as CSV.")
        return
    write_dicts_to_csv(data, path, overwrite=overwrite)


def save_json(data: Any, path: Path, overwrite: bool, indent: int) -> None:
    """Save data as JSON to the given path."""
    if not data:
        typer.echo("No data to save as JSON.")
        return
    validate_file_out(path, overwrite=overwrite)
    path.write_text(json.dumps(data, indent=indent))


def save_json_query(
    esi_query: EsiQuery, path: Path, overwrite: bool, indent: int
) -> None:
    """Save the EsiQuery as JSON to the given path."""
    validate_file_out(path, overwrite=overwrite)
    path.write_text(esi_query.model_dump_json(indent=indent))


def debug_print_split_parameters(
    ctx: typer.Context, parameters: Sequence[str], split_parameters: SplitParameters
) -> None:
    if ctx.obj.debug:
        if split_parameters.path:
            typer.echo(
                f"Path parameters: {json.dumps(split_parameters.path, indent=2)}"
            )
        if split_parameters.query:
            typer.echo(
                f"Query parameters: {json.dumps(split_parameters.query, indent=2)}"
            )
        if split_parameters.header:
            typer.echo(
                f"Header parameters: {json.dumps(split_parameters.header, indent=2)}"
            )
        if split_parameters.unknown:
            typer.echo(
                f"Unknown parameters: {json.dumps(split_parameters.unknown, indent=2)}"
            )


def parse_params(params: list[str]) -> Sequence[dict[str, str]]:
    """Parse a list of parameter strings into a list of key-value dictionaries.

    Parameters are expected in the form of `key=value`.
    """
    params_list: list[dict[str, str]] = []
    for param in params:
        if "=" not in param:
            raise ValueError(f"Parameter '{param}' is not in key=value format.")
        key, value = param.split("=", 1)
        if not key or not value:
            raise ValueError(f"Parameter '{param}' is not in key=value format.")
        params_list.append({key: value})

    return params_list


def init_client(ctx: typer.Context) -> EsiClient:
    # FIXME client should be created during startup, and stored in ctx.obj so that the code is only in one place.
    schema_store = ctx.obj.schema_store
    # TODO use real cache.
    cache = EsiMemoryCache()
    schema_api = EsiApi.from_schema_store(schema_store)
    client = EsiClient(
        schema_api=schema_api,
        cache=cache,
    )
    return client
