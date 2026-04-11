"""ESI Link CLI - Requests Commands."""

import asyncio
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from esi_link.cli.helpers import (
    get_esi_link_settings_from_context,
    get_executor_from_settings_and_schema,
)
from esi_link.factory import EsiLinkObjectFactory
from esi_link.helpers.pydantic.serialize_as_json import (
    load_from_json,
    serialize_as_json,
)
from esi_link.helpers.pydantic.serialize_as_yaml import (
    load_from_yaml,
    serialize_as_yaml,
)
from esi_link.models_and_protocols import Request, RequestGroup

app = typer.Typer(no_args_is_help=True)


@app.command()
def execute(
    ctx: typer.Context,
    requests_file: Annotated[
        Path,
        typer.Argument(
            ...,
            help="Path to the RequestGroup file to execute. Supports JSON and YAML formats, determined by the file suffix.",
            file_okay=True,
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
):
    """Execute the ESI Link CLI command."""
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    if requests_file.suffix.lower() in [".yaml", ".yml"]:
        request_group = load_from_yaml(requests_file, RequestGroup)
    elif requests_file.suffix.lower() == ".json":
        request_group = load_from_json(requests_file, RequestGroup)
    else:
        raise ValueError(
            f"Unsupported file format: {requests_file.suffix}. Supported formats are .json, .yaml, and .yml."
        )

    executor = get_executor_from_settings_and_schema(settings=settings)
    response_group = asyncio.run(executor.do_requests(request_group))
    error_count = sum(
        len(x.network_exception_messages) for x in response_group.responses.values()
    )
    console.print(f"Execution complete. {error_count} errors detected.")
    if error_count > 0:
        for response in response_group.responses.values():
            if response.network_exception_messages:
                console.print(
                    f"Request {response.request.request_id} had the following errors:",
                    style="bold red",
                )
                for msg in response.network_exception_messages:
                    console.print(f"- {msg}", style="red")
                console.print("\n")


@app.command()
def validate(
    ctx: typer.Context,
    requests_file: Annotated[
        Path,
        typer.Argument(
            ...,
            help="Path to the RequestGroup file to validate. Supports JSON and YAML formats, determined by the file suffix.",
            file_okay=True,
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
):
    """Validate the ESI Link CLI command.

    Validates requests, and reports errors to console.
    """
    settings = get_esi_link_settings_from_context(ctx)
    console = Console()
    if requests_file.suffix.lower() in [".yaml", ".yml"]:
        request_group = load_from_yaml(requests_file, RequestGroup)
    elif requests_file.suffix.lower() == ".json":
        request_group = load_from_json(requests_file, RequestGroup)
    else:
        raise ValueError(
            f"Unsupported file format: {requests_file.suffix}. Supported formats are .json, .yaml, and .yml."
        )

    executor = get_executor_from_settings_and_schema(settings=settings)

    # async def validate_requests():

    #     try:
    #         await executor.validate_requests(request_group)
    #     except Exception as e:
    #         console.print(
    #             f"Request {request.request_id} failed validation with error: {str(e)}",
    #             style="bold red",
    #         )

    # asyncio.run(validate_requests(request_group.requests.values()))

    # TODO validate group here.


@app.command()
def group_stub(ctx: typer.Context):
    """Group stub command."""
    # output a stub RequestGroup to a file or terminal for use as a template.
    # Option for JSON or YAML output.

    settings = get_esi_link_settings_from_context(ctx)
    # Here you would add the logic for the group stub command using the settings
    print(f"Group stub with settings: {settings}")


@app.command()
def request_stub(ctx: typer.Context):
    """Stub command."""
    # output a stub Request to a file or terminal for use as a template.
    # Option for JSON or YAML output.
    # option to specify operation_id, and have parameters generated.

    settings = get_esi_link_settings_from_context(ctx)
    # Here you would add the logic for the stub command using the settings
    print(f"Stub with settings: {settings}")


@app.command()
def handlers(ctx: typer.Context):
    """Handlers command."""
    # List the available handlers for use in the RequestGroups, and their parameters.
    # Get the doc string from the handler for details?
    settings = get_esi_link_settings_from_context(ctx)
    # Here you would add the logic for the handlers command using the settings
    print(f"Handlers with settings: {settings}")
