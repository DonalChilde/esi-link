import json
import logging
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any
from uuid import uuid4

import typer
from esi_auth import CharacterToken, get_authorized_characters
from rich import print as rich_print

from esi_link.esi_client.esi_client import EsiClient
from esi_link.esi_client.models import EsiQuery, EsiQueryResult
from esi_link.esi_schema import operation_accessors as OA
from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol, SplitParameters
from esi_link.helpers.csv import write_dicts_to_csv
from esi_link.helpers.response_to_json import query_to_result
from esi_link.helpers.validate_file_out import validate_file_out

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
app = typer.Typer(no_args_is_help=True)


def validate_auth_params(
    esi_api: EsiApiProtocol,
    operation_id: str,
    character_id: int | None,
    client_id: int | None,
    client_alias: str | None,
) -> CharacterToken | None:
    """Validate authentication parameters for an operation.

    If the operation requires authentication, ensure that a character ID is provided
    and that the character is authorized. Return the CharacterToken if valid, else None.

    Args:
        esi_api: The ESI API instance to use for operation lookup.
        operation_id: The ID of the operation to check.
        character_id: The character ID to use for authentication.
        client_id: The client ID to use for authentication.
        client_alias: The client alias to use for authentication.
    """
    operation = esi_api.indexed_operation(operation_id)
    if OA.is_auth_required(operation):
        if character_id is None:
            typer.echo(
                f"Operation {operation_id} requires authentication. Please provide a character ID with --character-id or -c."
            )
            raise typer.Exit(code=1)
        try:
            authorized_characters = get_authorized_characters(
                client_id=client_id, client_alias=client_alias
            )
            character_token = authorized_characters.get(character_id)
            if character_token is None:
                typer.echo(
                    f"Character ID {character_id} is not authorized. Please authorize first using esi-auth."
                )
                raise typer.Exit(code=1)
            return character_token
        except Exception as e:
            typer.echo(f"Error retrieving authorized characters: {e}")
            raise typer.Exit(code=1) from e
    return None


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
    character_id: Annotated[
        int | None,
        typer.Option(
            "-c",
            "--character-id",
            help="Character ID to use for this request if authorization is required.",
        ),
    ] = None,
    client_id: Annotated[
        int | None,
        typer.Option(
            "-i",
            "--client-id",
            help="Client ID to use for this request if authorization is required.",
        ),
    ] = None,
    client_alias: Annotated[
        str | None,
        typer.Option(
            "-a",
            "--client-alias",
            help="Alias for the client ID to use for authorization. Either the client ID or client alias must be provided.",
        ),
    ] = None,
    csv_data: Annotated[
        Path | None,
        typer.Option("--csv", help="Path to save the query response as CSV."),
    ] = None,
    query_json: Annotated[
        Path | None,
        typer.Option(
            "-j",
            "--json",
            help="Path to save the completed query to a JSON file, with response data as json.",
        ),
    ] = None,
    query_text: Annotated[
        Path | None,
        typer.Option(
            "-t",
            "--text",
            help="Path to save the completed query to a JSON file, with response data as text.",
        ),
    ] = None,
    console: Annotated[
        bool,
        typer.Option(
            "-c",
            "--console-json",
            help="Print only the json data from a completed query to the console, without any metadata.",
        ),
    ] = False,
    console_query: Annotated[
        bool,
        typer.Option(
            "--console-query",
            help="Print the completed query to the console, with response data as text.",
        ),
    ] = False,
    json_indent: Annotated[
        int, typer.Option("-i", "--json-indent", help="Indent level for JSON output.")
    ] = 2,
    file_overwrite: Annotated[
        bool,
        typer.Option("-o", "--overwrite", help="Allow overwriting existing files."),
    ] = False,
):
    """Get ESI data.

    Example:
        esi-link query get GetMarketsRegionIdHistory -p region_id=10000002 -p type_id=34
    """

    start = perf_counter()
    if not any((console, console_query, csv_data, query_json, query_text)):
        typer.echo("No output selected, query aborted.")
        raise typer.Exit(code=1)

    typer.echo(f"Getting ESI data for operation ID: {operation_id}")
    client: EsiClient = ctx.obj.client
    # split input parameters into key, value pairs
    if character_id:
        parameters.append(f"character_id={character_id}")
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
    headers = split_parameters.header
    character_token = validate_auth_params(
        esi_api=ctx.obj.esi_api,
        operation_id=operation_id,
        character_id=character_id,
        client_id=client_id,
        client_alias=client_alias,
    )
    if character_token:
        headers["Authorization"] = f"Bearer {character_token.access_token}"

    # debug_print_split_parameters(ctx, parameters, split_parameters)
    esi_query = EsiQuery(
        query_id=uuid4(),
        operation_id=operation_id,
        path_parameters=split_parameters.path,
        query_parameters=split_parameters.query,
        headers=headers,
    )
    client.validate_query(esi_query)
    if client.is_paged(esi_query):
        if not any((csv_data, query_json, query_text)):
            rich_print(
                "[red]Warning: This operation is paged, and no output file was specified. Output is too large for terminal. Operation Aborted."
            )
            raise typer.Exit(code=1)
    logger.info(f"Executing ESI Query: {esi_query!r}")
    client.query(esi_query)
    logger.debug(f"ESI Query completed in {perf_counter() - start:.2f} seconds.")
    if esi_query.response is None:
        typer.echo("No response received for query. See logs for details.")
        raise typer.Exit(code=1)
    result = query_to_result(esi_query)
    if csv_data:
        if isinstance(result.response.data, list) and all(
            isinstance(item, dict)
            for item in result.response.data  # type: ignore
        ):
            save_csv(result.response.data, csv_data, file_overwrite)  # type: ignore
        elif isinstance(result.response.data, dict):  # type: ignore
            save_csv([result.response.data], csv_data, file_overwrite)  # type: ignore
        else:
            typer.echo(
                "Response data is not a list of dictionaries or a single dictionary. Cannot save as CSV."
            )
    if query_json:
        validate_file_out(query_json, overwrite=file_overwrite)
        query_json.write_text(
            EsiQueryResult.model_dump_json(result, indent=json_indent)
        )
    if query_text:
        validate_file_out(query_text, overwrite=file_overwrite)
        query_text.write_text(esi_query.model_dump_json(indent=json_indent))
    if console_query:
        rich_print(esi_query)
    if console:
        rich_print(result.response.data)  # pyright: ignore[reportUnknownMemberType]

    typer.echo(f"Completed in {perf_counter() - start:.2f} seconds.")
    logger.info(
        f"Get Query to {esi_query.response.real_url} completed in {perf_counter() - start:.2f} seconds."
    )


def save_csv(data: list[dict[str, Any]], path: Path, overwrite: bool) -> None:
    """Save data as CSV to the given path."""
    if not data:
        rich_print("[red]No data to save as CSV.")
        return
    write_dicts_to_csv(data, path, overwrite=overwrite)


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
