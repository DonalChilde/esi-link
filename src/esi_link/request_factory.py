"""Example ESI requests for testing and demonstration purposes."""

from typing import Literal
from uuid import UUID, uuid4

from esi_link.models_and_protocols import (
    Request,
    RequestGroup,
    ResponseGroupHandlerConfig,
    ResponseHandlerConfig,
)
from esi_link.type_defs import Lang


def esi_status(
    handlers: list[ResponseHandlerConfig] | None = None, lang: Lang = "en"
) -> Request:
    """Request factory for the GetStatus operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetStatus",
        path_parameters={},
        query_parameters={},
        auth_character_id=None,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def esi_changelog(
    handlers: list[ResponseHandlerConfig] | None = None, lang: Lang = "en"
) -> Request:
    """Request factory for the GetMetaChangelog operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetMetaChangelog",
        path_parameters={},
        query_parameters={},
        auth_character_id=None,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def market_types_with_active_orders(
    region_id: int = 10000002,
    handlers: list[ResponseHandlerConfig] | None = None,
    lang: Lang = "en",
) -> Request:
    """Request factory for the GetMarketsRegionIdTypes operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdTypes",
        path_parameters={"region_id": region_id},
        query_parameters={"page": 1},
        auth_character_id=None,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def character_stats(
    character_id: int,
    handlers: list[ResponseHandlerConfig] | None = None,
    lang: Lang = "en",
) -> Request:
    """Request factory for the GetCharactersCharacterIdAttributes operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCharactersCharacterIdAttributes",
        path_parameters={"character_id": character_id},
        query_parameters={},
        auth_character_id=character_id,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def market_history_group(
    region_id: int,
    type_ids: list[int],
    response_handlers: list[ResponseHandlerConfig] | None = None,
    group_handlers: list[ResponseGroupHandlerConfig] | None = None,
    lang: Lang = "en",
) -> RequestGroup:
    """Request factory for the GetMarketsRegionIdHistory operation with query parameters."""
    response_handlers = response_handlers or []
    group_handlers = group_handlers or []
    requests: dict[UUID, Request] = {}

    for type_id in type_ids:
        request = Request(
            request_id=uuid4(),
            operation_id="GetMarketsRegionIdHistory",
            path_parameters={"region_id": region_id},
            query_parameters={"type_id": type_id},
            auth_character_id=None,
            lang=lang,
            json_body=None,
            response_handlers=response_handlers,
        )
        requests[request.request_id] = request

    request_group = RequestGroup(
        group_id=uuid4(),
        description=f"Market History Requests for region {region_id} and {len(type_ids)} type_ids",
        requests=requests,
        response_group_handlers=group_handlers,
    )
    return request_group


def character_blueprints(
    character_id: int,
    handlers: list[ResponseHandlerConfig] | None = None,
    lang: Lang = "en",
) -> Request:
    """Request factory for the GetCharactersCharacterIdBlueprints operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCharactersCharacterIdBlueprints",
        path_parameters={"character_id": character_id},
        query_parameters={"page": 1},
        auth_character_id=character_id,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def character_information(
    character_id: int,
    handlers: list[ResponseHandlerConfig] | None = None,
    lang: Lang = "en",
) -> Request:
    """Request factory for the GetCharactersCharacterId operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCharactersCharacterId",
        path_parameters={"character_id": character_id},
        query_parameters={},
        auth_character_id=None,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def corporation_blueprints(
    corporation_id: int,
    character_id: int,
    handlers: list[ResponseHandlerConfig] | None = None,
    lang: Lang = "en",
) -> Request:
    """Request factory for the GetCorporationsCorporationIdBlueprints operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCorporationsCorporationIdBlueprints",
        path_parameters={"corporation_id": corporation_id},
        query_parameters={"page": 1},
        auth_character_id=character_id,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def corporation_jobs(
    corporation_id: int,
    character_id: int,
    include_completed: bool = False,
    handlers: list[ResponseHandlerConfig] | None = None,
    lang: Lang = "en",
) -> Request:
    """Request factory for the GetCorporationsCorporationIdIndustryJobs operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCorporationsCorporationIdIndustryJobs",
        path_parameters={"corporation_id": corporation_id},
        query_parameters={"page": 1, "include_completed": include_completed},
        auth_character_id=character_id,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def character_jobs(
    character_id: int,
    include_completed: bool = False,
    handlers: list[ResponseHandlerConfig] | None = None,
    lang: Lang = "en",
) -> Request:
    """Request factory for the GetCharactersCharacterIdIndustryJobs operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCharactersCharacterIdIndustryJobs",
        path_parameters={"character_id": character_id},
        query_parameters={"include_completed": include_completed},
        auth_character_id=character_id,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def markets_prices(
    handlers: list[ResponseHandlerConfig] | None = None, lang: Lang = "en"
) -> Request:
    """Request factory for the GetMarketsPrices operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetMarketsPrices",
        path_parameters={},
        query_parameters={},
        auth_character_id=None,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )


def market_orders(
    region_id: int,
    order_type: Literal["all", "buy", "sell"] = "all",
    type_id: int | None = None,
    handlers: list[ResponseHandlerConfig] | None = None,
    lang: Lang = "en",
) -> Request:
    """Request factory for the GetMarketsRegionIdOrders operation."""
    handlers = handlers or []
    query_parameters: dict[str, int | str | float] = {"page": 1}
    if order_type in ("buy", "sell"):
        query_parameters["order_type"] = order_type
    else:
        query_parameters["order_type"] = "all"
    if type_id is not None:
        query_parameters["type_id"] = type_id
    return Request(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdOrders",
        path_parameters={"region_id": region_id},
        query_parameters=query_parameters,
        auth_character_id=None,
        lang=lang,
        json_body=None,
        response_handlers=handlers,
    )
