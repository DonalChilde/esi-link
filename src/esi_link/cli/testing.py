import asyncio
import json
from uuid import uuid4

import typer
from rich.console import Console
from rich.json import JSON

from esi_link.cli.helpers import get_settings_from_context
from esi_link.v3.factory import EsiLinkObjectFactory
from esi_link.v3.models_and_protocols import Request, RequestGroup
from esi_link.v3.schema.schema_manager import SchemaManager

app = typer.Typer(
    no_args_is_help=True, help="Commands for testing ESI Link functionality."
)
from esi_link.v3 import example_requests


@app.command()
def status(ctx: typer.Context):
    """Run tests for ESI Link."""
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Running tests...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    schema = schema_manager.get_latest_schema()
    request = example_requests.esi_status()
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    factory = EsiLinkObjectFactory(
        schema=schema,
        cache_type="json",
        cache_directory=settings.json_cache_directory,
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
    )
    group_executor = factory.group_executor()
    response_group = asyncio.run(group_executor(request_group))
    response = response_group.responses[request.request_id]
    console.print(response.http_response)


@app.command()
def pages(ctx: typer.Context):
    """Test handling of paged requests."""
    settings = get_settings_from_context(ctx)
    console = Console()
    console.print("Running tests...")
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    schema = schema_manager.get_latest_schema()
    request = example_requests.market_types_with_active_orders()
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )

    factory = EsiLinkObjectFactory(
        schema=schema,
        cache_type="json",
        cache_directory=settings.json_cache_directory,
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
    )
    group_executor = factory.group_executor()
    response_group = asyncio.run(group_executor(request_group))
    response = response_group.responses[request.request_id]
    data = json.loads(response.http_response.body_text)
    console.print(f"Total items: {len(data)}")
    console.print(JSON.from_data(data))
