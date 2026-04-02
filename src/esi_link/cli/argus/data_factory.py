"""Data factory functions for Argus commands."""

import asyncio
from uuid import uuid4

import typer
from rich.console import Console

from esi_link import request_factory as request_factory
from esi_link.api import EsiLink
from esi_link.argus import models as argus_models
from esi_link.helpers.make_response_data import make_response_data
from esi_link.models_and_protocols import RequestGroup
from esi_link.type_defs import Lang


def get_character_blueprints(
    executor: EsiLink, character_id: int, console: Console, lang: Lang = "en"
) -> argus_models.GetCharactersCharacterIdBlueprints:
    """Helper function to get character blueprints for a given character ID."""
    char_bp_request = request_factory.character_blueprints(
        character_id=character_id, lang=lang
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={char_bp_request.request_id: char_bp_request}
    )
    try:
        response_group = asyncio.run(executor.do_requests(request_group))
    except Exception as e:
        console.print(f"[red]Error executing request: {e}[/red]")
        raise typer.Exit(code=1) from e
    response = response_group.responses.get(char_bp_request.request_id)
    if response is None:
        console.print(
            f"[red]No response received for request {char_bp_request.request_id}[/red]"
        )
        raise typer.Exit(code=1)
    try:
        response_data = make_response_data(response)
        argus_blueprints = (
            argus_models.GetCharactersCharacterIdBlueprints.from_response_data(
                response_data=response_data
            )
        )
        return argus_blueprints
    except ValueError as e:
        console.print(f"[red]Error processing response data: {e}[/red]")
        raise typer.Exit(code=1) from e


def get_character_information(
    executor: EsiLink, character_id: int, console: Console, lang: Lang = "en"
) -> argus_models.GetCharactersCharacterId:
    """Helper function to get character information for a given character ID."""
    char_info_request = request_factory.character_information(
        character_id=character_id, lang=lang
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={char_info_request.request_id: char_info_request}
    )
    try:
        response_group = asyncio.run(executor.do_requests(request_group))
    except Exception as e:
        console.print(f"[red]Error executing request: {e}[/red]")
        raise typer.Exit(code=1) from e
    response = response_group.responses.get(char_info_request.request_id)
    if response is None:
        console.print(
            f"[red]No response received for request {char_info_request.request_id}[/red]"
        )
        raise typer.Exit(code=1)
    try:
        response_data = make_response_data(response)
        char_info = argus_models.GetCharactersCharacterId.from_response_data(
            response_data=response_data
        )
        return char_info
    except ValueError as e:
        console.print(f"[red]Error processing response data: {e}[/red]")
        raise typer.Exit(code=1) from e


def get_character_jobs(
    executor: EsiLink,
    character_id: int,
    include_completed: bool,
    console: Console,
    lang: Lang = "en",
) -> argus_models.GetCharactersCharacterIdIndustryJobs:
    """Helper function to get character jobs for a given character ID."""
    char_jobs_request = request_factory.character_jobs(
        character_id=character_id, include_completed=include_completed, lang=lang
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={char_jobs_request.request_id: char_jobs_request}
    )
    try:
        response_group = asyncio.run(executor.do_requests(request_group))
    except Exception as e:
        console.print(f"[red]Error executing request: {e}[/red]")
        raise typer.Exit(code=1) from e
    response = response_group.responses.get(char_jobs_request.request_id)
    if response is None:
        console.print(
            f"[red]No response received for request {char_jobs_request.request_id}[/red]"
        )
        raise typer.Exit(code=1)
    try:
        response_data = make_response_data(response)
        char_jobs = (
            argus_models.GetCharactersCharacterIdIndustryJobs.from_response_data(
                response_data=response_data
            )
        )
        return char_jobs
    except ValueError as e:
        console.print(f"[red]Error processing response data: {e}[/red]")
        raise typer.Exit(code=1) from e


def get_corporation_blueprints(
    executor: EsiLink,
    corporation_id: int,
    character_id: int,
    console: Console,
    lang: Lang = "en",
) -> argus_models.GetCorporationsCorporationIdBlueprints:
    """Helper function to get corporation blueprints for a given corporation ID."""
    corp_bp_request = request_factory.corporation_blueprints(
        corporation_id=corporation_id, character_id=character_id, lang=lang
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={corp_bp_request.request_id: corp_bp_request}
    )
    try:
        response_group = asyncio.run(executor.do_requests(request_group))
    except Exception as e:
        console.print(f"[red]Error executing request: {e}[/red]")
        raise typer.Exit(code=1) from e
    response = response_group.responses.get(corp_bp_request.request_id)
    if response is None:
        console.print(
            f"[red]No response received for request {corp_bp_request.request_id}[/red]"
        )
        raise typer.Exit(code=1)
    try:
        response_data = make_response_data(response)
        corp_blueprints = (
            argus_models.GetCorporationsCorporationIdBlueprints.from_response_data(
                response_data=response_data
            )
        )
        return corp_blueprints
    except ValueError as e:
        console.print(f"[red]Error processing response data: {e}[/red]")
        raise typer.Exit(code=1) from e


def get_corporation_jobs(
    executor: EsiLink,
    corporation_id: int,
    character_id: int,
    include_completed: bool,
    console: Console,
    lang: Lang = "en",
) -> argus_models.GetCorporationsCorporationIdIndustryJobs:
    """Helper function to get corporation jobs for a given corporation ID."""
    corp_jobs_request = request_factory.corporation_jobs(
        corporation_id=corporation_id,
        character_id=character_id,
        include_completed=include_completed,
        lang=lang,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={corp_jobs_request.request_id: corp_jobs_request}
    )
    try:
        response_group = asyncio.run(executor.do_requests(request_group))
    except Exception as e:
        console.print(f"type of exception: {type(e)}")
        console.print(f"[red]Error executing request: {e}[/red]")
        raise typer.Exit(code=1) from e
    response = response_group.responses.get(corp_jobs_request.request_id)
    if response is None:
        console.print(
            f"[red]No response received for request {corp_jobs_request.request_id}[/red]"
        )
        raise typer.Exit(code=1)
    try:
        response_data = make_response_data(response)
        corp_jobs = (
            argus_models.GetCorporationsCorporationIdIndustryJobs.from_response_data(
                response_data=response_data
            )
        )
        return corp_jobs
    except ValueError as e:
        console.print(f"[red]Error processing response data: {e}[/red]")
        raise typer.Exit(code=1) from e


def get_universe_market_prices(
    executor: EsiLink, console: Console, lang: Lang = "en"
) -> argus_models.GetMarketsPrices:
    """Helper function to get universe market prices."""
    market_prices_request = request_factory.markets_prices(lang=lang)
    request_group = RequestGroup(
        group_id=uuid4(),
        requests={market_prices_request.request_id: market_prices_request},
    )
    try:
        response_group = asyncio.run(executor.do_requests(request_group))
    except Exception as e:
        console.print(f"[red]Error executing request: {e}[/red]")
        raise typer.Exit(code=1) from e
    response = response_group.responses.get(market_prices_request.request_id)
    if response is None:
        console.print(
            f"[red]No response received for request {market_prices_request.request_id}[/red]"
        )
        raise typer.Exit(code=1)
    try:
        response_data = make_response_data(response)
        market_prices = argus_models.GetMarketsPrices.from_response_data(
            response_data=response_data
        )
        return market_prices
    except ValueError as e:
        console.print(f"[red]Error processing response data: {e}[/red]")
        raise typer.Exit(code=1) from e


def get_market_orders_for_region(
    executor: EsiLink, region_id: int, console: Console, lang: Lang = "en"
) -> argus_models.GetMarketsRegionIdOrders:
    """Helper function to get market orders for a given region ID."""
    market_orders_request = request_factory.market_orders(
        region_id=region_id, lang=lang
    )
    request_group = RequestGroup(
        group_id=uuid4(),
        requests={market_orders_request.request_id: market_orders_request},
    )
    try:
        response_group = asyncio.run(executor.do_requests(request_group))
    except Exception as e:
        console.print(f"[red]Error executing request: {e}[/red]")
        raise typer.Exit(code=1) from e
    response = response_group.responses.get(market_orders_request.request_id)
    if response is None:
        console.print(
            f"[red]No response received for request {market_orders_request.request_id}[/red]"
        )
        raise typer.Exit(code=1)
    try:
        response_data = make_response_data(response)
        market_orders = argus_models.GetMarketsRegionIdOrders.from_response_data(
            response_data=response_data
        )
        return market_orders
    except ValueError as e:
        console.print(f"[red]Error processing response data: {e}[/red]")
        raise typer.Exit(code=1) from e
