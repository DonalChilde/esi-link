import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from eve_static_data import ESDLoader

from esi_link import EsiLink, request_factory
from esi_link.argus.calculations.sde_lookups import blueprints_in_market
from esi_link.argus.models import (
    GetCharactersCharacterIdBlueprints,
    GetCorporationsCorporationIdBlueprints,
)
from esi_link.helpers.dict_writer import write_dicts_to_csv
from esi_link.helpers.make_response_data import make_response_data
from esi_link.models_and_protocols import RequestGroup, ResponseGroup
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
    output_file: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="Optional path to output the missing blueprints to a JSON file.",
        ),
    ] = None,
):
    sde_loader = ESDLoader(sde_path)
    eve_types = sde_loader.derived_datasets.normalized_eve_types()
    market_paths = sde_loader.derived_datasets.market_paths()
    response_group = make_requests(
        character_id=character_id, corporation_id=corporation_id
    )
    character_blueprints, corporation_blueprints = structure_responses(response_group)

    owned_blueprints = set(character_blueprints.blueprints) | set(
        corporation_blueprints.blueprints
    )
    blueprints_dataset = sde_loader.sde_datasets.blueprints()
    blueprints_in_market_set = blueprints_in_market(
        blueprints=blueprints_dataset,
        normalized_eve_types=eve_types,
        only_published=True,
    )
    missing_blueprints = blueprints_in_market_set - owned_blueprints

    if missing_blueprints:
        print("Missing blueprints that are in the market:")
        msgs: list[dict[str, str | int]] = []
        for blueprint_id in missing_blueprints:
            eve_type = eve_types.records.get(blueprint_id)
            if eve_type:
                market_group_id = eve_type.marketGroupID
                market_path = (
                    market_paths.records.get(market_group_id)
                    if market_group_id
                    else None
                )
                info: dict[str, str | int] = {
                    "type_id": blueprint_id,
                    "market_path": market_path.delimited_str_path()
                    if market_path
                    else "Unknown path",
                    "name": eve_type.name,
                }
            else:
                info = {
                    "type_id": blueprint_id,
                    "market_path": "Unknown path",
                    "name": "Unknown type",
                }
            msgs.append(info)
        msgs.sort(key=lambda x: (x["market_path"], x["name"]))
        if output_file:
            rows_written = write_dicts_to_csv(
                dicts=msgs, file_path=output_file, overwrite=True
            )
            print(f"Wrote {rows_written} missing blueprints to {output_file}")
        else:
            for msg in msgs:
                print(msg)


def structure_responses(
    response_group: ResponseGroup,
) -> tuple[GetCharactersCharacterIdBlueprints, GetCorporationsCorporationIdBlueprints]:
    """Helper function to structure responses by endpoint."""
    character_blueprints_response = None
    corporation_blueprints_response = None
    for response in response_group.responses.values():
        response_data = make_response_data(response)
        if response_data.request.operation_id == "GetCharactersCharacterIdBlueprints":
            character_blueprints_response = (
                GetCharactersCharacterIdBlueprints.from_response_data(response_data)
            )
        elif (
            response_data.request.operation_id
            == "GetCorporationsCorporationIdBlueprints"
        ):
            corporation_blueprints_response = (
                GetCorporationsCorporationIdBlueprints.from_response_data(response_data)
            )
        else:
            raise ValueError(
                f"Unexpected operation ID in response: {response_data.request.operation_id}"
            )
    if character_blueprints_response is None or corporation_blueprints_response is None:
        raise ValueError(
            "Missing expected responses for character or corporation blueprints"
        )
    return character_blueprints_response, corporation_blueprints_response


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
    _ = validation
    response_group = asyncio.run(esi_link.do_requests(request_group))
    return response_group


if __name__ == "__main__":
    app()
