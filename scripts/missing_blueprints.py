import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from eve_static_data import ESDLoader

from esi_link import EsiLink, request_factory
from esi_link.calculations.sde_lookups import blueprints_in_market
from esi_link.models_and_protocols import Request, RequestGroup, ResponseGroup
from esi_link.schema.schema_manager import SchemaManager
from esi_link.settings import get_settings

app = typer.Typer(no_args_is_help=True)


@app.command()
def check_blueprints(
    sde_path: Annotated[
        Path, typer.Argument(help="Path to the EVE Static Data Export (SDE) directory")
    ],
    character_id: Annotated[
        int, typer.Argument(help="EVE Online character ID to check blueprints for")
    ],
    corporation_id: Annotated[
        int | None,
        typer.Option(
            "-c",
            "--corporation",
            help="The corporation ID to check blueprints for, if desired.",
        ),
    ] = None,
):
    sde_loader = ESDLoader(sde_path)
    eve_types = sde_loader.derived_datasets.normalized_eve_types()
    response_group = make_requests(
        character_id=character_id, corporation_id=corporation_id
    )
    owned_blueprints = get_owned_blueprints_from_response_group(response_group)
    blueprints_dataset = sde_loader.sde_datasets.blueprints()
    blueprints_in_market_set = blueprints_in_market(
        blueprints=blueprints_dataset,
        normalized_eve_types=eve_types,
        only_published=True,
    )
    missing_blueprints = blueprints_in_market_set - owned_blueprints

    if missing_blueprints:
        print("Missing blueprints that are in the market:")
        msgs: list[str] = []
        market_paths = sde_loader.derived_datasets.market_paths()
        for blueprint_id in missing_blueprints:
            eve_type = eve_types.records.get(blueprint_id)
            if eve_type:
                marketGroupID = eve_type.marketGroupID
                market_path = (
                    market_paths.records.get(marketGroupID) if marketGroupID else None
                )
                msgs.append(
                    f"{market_path.str_string_path() if market_path else 'Unknown path'}- {eve_type.name} (type ID: {blueprint_id})"
                )
            else:
                msgs.append(f"- Unknown blueprint with type ID: {blueprint_id}")
        msgs.sort()
        for msg in msgs:
            print(msg)


def get_owned_blueprints_from_response_group(response_group: ResponseGroup) -> set[int]:
    """Helper function to extract owned blueprint type IDs from a ResponseGroup."""
    owned_blueprints: set[int] = set()
    for response in response_group.responses.values():
        if response.network_exception_messages:
            print(
                f"Error in request {response.request.request_id}: {response.network_exception_messages}"
            )
            continue
        if response.http_response is None:
            print(f"No HTTP response for request {response.request.request_id}")
            continue
        data = response.http_response.body_json
        if isinstance(data, list):
            for item in data:
                type_id = item.get("type_id")
                if type_id is not None:
                    owned_blueprints.add(type_id)
    return owned_blueprints


def make_requests(
    character_id: int, corporation_id: int | None = None
) -> ResponseGroup:
    """Helper function to create a RequestGroup for character and corporation blueprints."""
    settings = get_settings()
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    esi_link = EsiLink(
        schema=stored_schema.esi_schema,
        cache_type="diskcache",
        cache_directory=settings.cache_directory,
        credentials_file=settings.app_credentials_file,
        tokens_dir=settings.tokens_dir,
    )

    character_request = request_factory.character_blueprints(character_id=character_id)
    if corporation_id:
        corporation_request = request_factory.corporation_blueprints(
            character_id=character_id, corporation_id=corporation_id
        )
    else:
        corporation_request = None
    request_group = RequestGroup(
        group_id=uuid4(),
        requests={character_request.request_id: character_request},
    )
    if corporation_request:
        request_group.requests[corporation_request.request_id] = corporation_request

    validation = asyncio.run(esi_link.validate_requests(request_group))
    response_group = asyncio.run(esi_link.do_requests(request_group))
    return response_group


if __name__ == "__main__":
    app()
