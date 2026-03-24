"""Example Esi Requests."""

import asyncio
import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from rich.console import Console
from rich.json import JSON

from esi_link.cli.helpers import factory_from_settings, get_settings_from_context
from esi_link.factory import EsiLinkObjectFactory
from esi_link.models_and_protocols import RequestGroup, Response
from esi_link.schema.schema_manager import SchemaManager

app = typer.Typer(
    no_args_is_help=True, help="Commands for testing ESI Link functionality."
)
from esi_link import example_requests


@app.command()
def status(
    ctx: typer.Context,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "-d", "--directory", help="Directory to save the status response to."
        ),
    ] = None,
):
    """Run tests for ESI Link."""
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Preparing request...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    request = example_requests.esi_status(
        handlers=[
            example_requests.debug_file_response(output_dir=output_dir),
            example_requests.standard_file_response(output_dir=output_dir),
            example_requests.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    factory = EsiLinkObjectFactory(
        schema=stored_schema.esi_schema,
        cache_type="json",
        cache_directory=settings.json_cache_directory,
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
    )
    console.print(f"Requesting data from {request.operation_id} endpoint...")
    group_executor = factory.group_executor()
    response_group = asyncio.run(group_executor(request_group))
    response = response_group.responses[request.request_id]
    if output_dir:
        console.print(f"Status response saved to {output_dir}")
    # The caller is responsible for checking for exceptions in the response and handling
    # them appropriately.
    check_for_exceptions(response, console)
    console.print(JSON(response.http_response.body_text))  # type: ignore


@app.command()
def pages(
    ctx: typer.Context,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "-d", "--directory", help="Directory to save the paged response to."
        ),
    ] = None,
):
    """Test handling of paged requests."""
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Preparing request...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    request = example_requests.market_types_with_active_orders(
        handlers=[
            example_requests.debug_file_response(output_dir=output_dir),
            example_requests.standard_file_response(output_dir=output_dir),
            example_requests.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    factory = EsiLinkObjectFactory(
        schema=stored_schema.esi_schema,
        cache_type="json",
        cache_directory=settings.json_cache_directory,
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
    )
    console.print(f"Requesting data from {request.operation_id} endpoint...")
    group_executor = factory.group_executor()
    response_group = asyncio.run(group_executor(request_group))
    response = response_group.responses[request.request_id]
    if output_dir:
        console.print(f"Paged response saved to {output_dir}")
    # The caller is responsible for checking for exceptions in the response and handling
    # them appropriately.
    check_for_exceptions(response, console)
    try:
        data = json.loads(response.http_response.body_text)  # type: ignore
    except Exception as e:
        console.print(f"Failed to decode JSON: {e}")
        raise typer.Exit(code=1) from e
    console.print(f"Total items: {len(data)}")
    console.print(JSON.from_data(data))


@app.command()
def changelog(
    ctx: typer.Context,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "-d", "--directory", help="Directory to save the changelog response to."
        ),
    ] = None,
):
    """Test a request with an optional response handler."""
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Preparing request...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    request = example_requests.esi_changelog(
        handlers=[
            example_requests.debug_file_response(output_dir=output_dir),
            example_requests.standard_file_response(output_dir=output_dir),
            example_requests.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    factory = EsiLinkObjectFactory(
        schema=stored_schema.esi_schema,
        cache_type="json",
        cache_directory=settings.json_cache_directory,
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
    )
    console.print(f"Requesting data from {request.operation_id} endpoint...")
    group_executor = factory.group_executor()
    response_group = asyncio.run(group_executor(request_group))
    response = response_group.responses[request.request_id]
    if output_dir:
        console.print(f"Changelog response saved to {output_dir}")
    # The caller is responsible for checking for exceptions in the response and handling
    # them appropriately.
    check_for_exceptions(response, console)
    console.print(JSON(response.http_response.body_text))  # type: ignore


@app.command()
def character_stats(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(..., help="The character ID to get stats for.")
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "-d",
            "--directory",
            help="Directory to save the character stats response to.",
        ),
    ] = None,
):
    """Test a request with an optional response handler."""
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Preparing request...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    request = example_requests.character_stats(
        character_id=character_id,
        handlers=[
            example_requests.debug_file_response(output_dir=output_dir),
            example_requests.standard_file_response(output_dir=output_dir),
            example_requests.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    factory = EsiLinkObjectFactory(
        schema=stored_schema.esi_schema,
        cache_type="json",
        cache_directory=settings.json_cache_directory,
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
    )
    console.print(f"Requesting data from {request.operation_id} endpoint...")
    group_executor = factory.group_executor()
    response_group = asyncio.run(group_executor(request_group))
    response = response_group.responses[request.request_id]
    if output_dir:
        console.print(f"Character stats response saved to {output_dir}")
    # The caller is responsible for checking for exceptions in the response and handling
    # them appropriately.
    check_for_exceptions(response, console)
    console.print(JSON(response.http_response.body_text))  # type: ignore


@app.command()
def market_history(
    ctx: typer.Context,
    region_id: Annotated[
        int, typer.Argument(..., help="The region ID to get market history for.")
    ],
    output_dir: Annotated[
        Path,
        typer.Argument(..., help="Directory to save the market history responses to."),
    ],
):
    """Test a request group with multiple requests.

    Gets the market history for the first 100 type IDs in the specified region, with
    one request per type ID. Saves the responses to a JSONL file in the specified output
    directory, and any response errors in an `errors` subdirectory.
    """
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Preparing request group...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    factory = factory_from_settings(settings, stored_schema.esi_schema)
    console.print("Fetching type IDs for market history requests...")
    type_ids_request = example_requests.market_types_with_active_orders()
    type_ids_group = RequestGroup(
        group_id=uuid4(), requests={type_ids_request.request_id: type_ids_request}
    )
    group_executor = factory.group_executor()
    type_ids_response_group = asyncio.run(group_executor(type_ids_group))
    try:
        type_ids = json.loads(
            type_ids_response_group.responses[
                type_ids_request.request_id
            ].http_response.body_text  # type: ignore
        )
    except Exception as e:
        console.print(f"Failed to decode JSON for type IDs: {e}")
        raise typer.Exit(code=1) from e
    console.print(
        f"Found {len(type_ids)} type IDs with active orders in region {region_id}. Preparing market history requests..."
    )
    console.print(
        "Note: Only the first 100 type IDs will be included in the market history request group to avoid excessive requests."
    )
    type_id_list = type_ids[
        :100
    ]  # Get the first 100 type IDs for the market history requests
    request_group = example_requests.market_history_group(
        region_id=region_id,
        type_ids=type_id_list,
        response_handlers=[
            example_requests.only_on_error_file_response(
                output_dir=output_dir / "errors"
            )
        ],
        group_handlers=[
            example_requests.save_group_as_jsonl(output_dir=output_dir),
            example_requests.save_group_stats(output_dir=output_dir),
        ],
    )

    console.print(f"Requesting market history for region {region_id}...")
    response_group = asyncio.run(group_executor(request_group))
    console.print(f"Response count: {len(response_group.responses)}")
    console.print(
        f"Group handler exception messages: {response_group.group_handler_exception_messages}"
    )
    console.print(f"Group handler exceptions: {response_group.exceptions}")
    console.print(
        f"Group hanlder save path: {response_group.runtime_info.response_group_handlers[0].file_path if response_group.runtime_info.response_group_handlers else 'N/A'}"
    )
    console.print(f"Market history responses saved to {output_dir}")


def check_for_exceptions(response: Response, console: Console) -> None:
    """Check for exceptions in the response and print them to the console."""
    if response.network_exception_messages:
        console.print("Network exceptions occurred:")
        for msg in response.network_exception_messages:
            console.print(f"- {msg}")
        raise typer.Exit(code=1)
    if response.handler_exception_messages:
        console.print("Response handler exceptions occurred:")
        for msg in response.handler_exception_messages:
            console.print(f"- {msg}")


# TODO add display function to report perf and cache status of response
# TODO add display function to report same for a group.
