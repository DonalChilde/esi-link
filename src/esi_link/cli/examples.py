"""Example Esi Requests."""

import asyncio
import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from rich.console import Console
from rich.json import JSON

import esi_link.handler_factory
from esi_link.cli.helpers import (
    get_executor_from_settings_and_schema,
    get_settings_from_context,
)
from esi_link.cli.response_display_helpers import display_response_group_summary
from esi_link.models_and_protocols import RequestGroup, Response
from esi_link.schema.schema_manager import SchemaManager

app = typer.Typer(
    no_args_is_help=True, help="Commands for testing ESI Link functionality."
)
from esi_link import request_factory


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
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )

    request = request_factory.esi_status(
        handlers=[
            esi_link.handler_factory.debug_file_response(output_dir=output_dir),
            esi_link.handler_factory.standard_file_response(output_dir=output_dir),
            esi_link.handler_factory.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    console.print(f"Requesting data from {request.operation_id} endpoint...")

    response_group = asyncio.run(executor.do_requests(request_group))
    console.print(f"Response Group Summary:")
    display_response_group_summary(response_group, console)
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
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )
    request = request_factory.market_types_with_active_orders(
        handlers=[
            esi_link.handler_factory.debug_file_response(output_dir=output_dir),
            esi_link.handler_factory.standard_file_response(output_dir=output_dir),
            esi_link.handler_factory.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    console.print(f"Requesting data from {request.operation_id} endpoint...")
    response_group = asyncio.run(executor.do_requests(request_group))
    console.print(f"Response Group Summary:")
    display_response_group_summary(response_group, console)
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
    console.print("First 10 items:")
    console.print(data[:10])


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
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )
    request = request_factory.esi_changelog(
        handlers=[
            esi_link.handler_factory.debug_file_response(output_dir=output_dir),
            esi_link.handler_factory.standard_file_response(output_dir=output_dir),
            esi_link.handler_factory.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    console.print(f"Requesting data from {request.operation_id} endpoint...")
    response_group = asyncio.run(executor.do_requests(request_group))
    console.print(f"Response Group Summary:")
    display_response_group_summary(response_group, console)
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
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )
    request = request_factory.character_stats(
        character_id=character_id,
        handlers=[
            esi_link.handler_factory.debug_file_response(output_dir=output_dir),
            esi_link.handler_factory.standard_file_response(output_dir=output_dir),
            esi_link.handler_factory.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    console.print(f"Requesting data from {request.operation_id} endpoint...")
    response_group = asyncio.run(executor.do_requests(request_group))
    console.print(f"Response Group Summary:")
    display_response_group_summary(response_group, console)
    response = response_group.responses[request.request_id]
    if output_dir:
        console.print(f"Character stats response saved to {output_dir}")
    # The caller is responsible for checking for exceptions in the response and handling
    # them appropriately.
    check_for_exceptions(response, console)
    console.print(JSON(response.http_response.body_text))  # type: ignore


@app.command()
def character_info(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(..., help="The character ID to get info for.")
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "-d",
            "--directory",
            help="Directory to save the character info response to.",
        ),
    ] = None,
):
    """Example ESI request for the GetCharactersCharacterId operation."""
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Preparing request...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )
    request = request_factory.character_information(
        character_id=character_id,
        handlers=[
            esi_link.handler_factory.debug_file_response(output_dir=output_dir),
            esi_link.handler_factory.standard_file_response(output_dir=output_dir),
            esi_link.handler_factory.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    console.print(f"Requesting data from {request.operation_id} endpoint...")
    response_group = asyncio.run(executor.do_requests(request_group))
    console.print(f"Response Group Summary:")
    display_response_group_summary(response_group, console)
    response = response_group.responses[request.request_id]
    if output_dir:
        console.print(f"Character stats response saved to {output_dir}")
    # The caller is responsible for checking for exceptions in the response and handling
    # them appropriately.
    check_for_exceptions(response, console)
    console.print(JSON(response.http_response.body_text))  # type: ignore


@app.command()
def corporation_blueprints(
    ctx: typer.Context,
    corporation_id: Annotated[
        int, typer.Argument(..., help="The corporation ID to get blueprints for.")
    ],
    character_id: Annotated[
        int, typer.Argument(..., help="The character ID to get info for.")
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "-d",
            "--directory",
            help="Directory to save the character info response to.",
        ),
    ] = None,
):
    """Example ESI request for the GetCorporationsCorporationIdBlueprints operation."""
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Preparing request...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )
    request = request_factory.corporation_blueprints(
        corporation_id=corporation_id,
        character_id=character_id,
        handlers=[
            esi_link.handler_factory.debug_file_response(output_dir=output_dir),
            esi_link.handler_factory.standard_file_response(output_dir=output_dir),
            esi_link.handler_factory.detailed_file_response(output_dir=output_dir),
        ]
        if output_dir
        else None,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    console.print(f"Requesting data from {request.operation_id} endpoint...")
    response_group = asyncio.run(executor.do_requests(request_group))
    console.print(f"Response Group Summary:")
    display_response_group_summary(response_group, console)
    response = response_group.responses[request.request_id]
    check_for_exceptions(response, console)
    if output_dir:
        console.print(f"Corporation blueprints response saved to {output_dir}")
    # The caller is responsible for checking for exceptions in the response and handling
    # them appropriately.
    else:
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
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )
    console.print("Fetching type IDs for market history requests...")
    type_ids_request = request_factory.market_types_with_active_orders()
    type_ids_group = RequestGroup(
        group_id=uuid4(), requests={type_ids_request.request_id: type_ids_request}
    )
    type_ids_response_group = asyncio.run(executor.do_requests(type_ids_group))
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
    request_group = request_factory.market_history_group(
        region_id=region_id,
        type_ids=type_id_list,
        response_handlers=[
            esi_link.handler_factory.only_on_error_file_response(
                output_dir=output_dir / "errors"
            )
        ],
        group_handlers=[
            esi_link.handler_factory.save_group_as_jsonl(output_dir=output_dir),
            esi_link.handler_factory.save_group_stats(output_dir=output_dir),
        ],
    )

    console.print(f"Requesting market history for region {region_id}...")
    response_group = asyncio.run(executor.do_requests(request_group))
    console.print(f"Response Group Summary:")
    display_response_group_summary(response_group, console)
    console.print(
        f"Group handler save path: {response_group.runtime_info.response_group_handlers[0].file_path if response_group.runtime_info.response_group_handlers else 'N/A'}"
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
