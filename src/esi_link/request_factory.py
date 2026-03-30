"""Example ESI requests for testing and demonstration purposes."""

from uuid import UUID, uuid4

from esi_link.models_and_protocols import (
    Request,
    RequestGroup,
    ResponseGroupHandlerConfig,
    ResponseHandlerConfig,
)


def esi_status(handlers: list[ResponseHandlerConfig] | None = None) -> Request:
    """Example ESI request for the /status endpoint."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetStatus",
        path_parameters={},
        query_parameters={},
        auth_character_id=None,
        lang="en",
        json_body=None,
        response_handlers=handlers,
    )


def esi_changelog(handlers: list[ResponseHandlerConfig] | None = None) -> Request:
    """Example ESI request for the /meta/changelog endpoint."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetMetaChangelog",
        path_parameters={},
        query_parameters={},
        auth_character_id=None,
        lang="en",
        json_body=None,
        response_handlers=handlers,
    )


def market_types_with_active_orders(
    region_id: int = 10000002, handlers: list[ResponseHandlerConfig] | None = None
) -> Request:
    """Example ESI request for the /markets/{region_id}/types/ endpoint with a query parameter."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdTypes",
        path_parameters={"region_id": region_id},
        query_parameters={"page": 1},
        auth_character_id=None,
        lang="en",
        json_body=None,
        response_handlers=handlers,
    )


def character_stats(
    character_id: int, handlers: list[ResponseHandlerConfig] | None = None
) -> Request:
    """Example ESI request for the GetCharactersCharacterIdAttributes operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCharactersCharacterIdAttributes",
        path_parameters={"character_id": character_id},
        query_parameters={},
        auth_character_id=character_id,
        lang="en",
        json_body=None,
        response_handlers=handlers,
    )


def market_history_group(
    region_id: int,
    type_ids: list[int],
    response_handlers: list[ResponseHandlerConfig] | None = None,
    group_handlers: list[ResponseGroupHandlerConfig] | None = None,
) -> RequestGroup:
    """Example ESI request for the /markets/{region_id}/history/ endpoint with query parameters."""
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
            lang="en",
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
    character_id: int, handlers: list[ResponseHandlerConfig] | None = None
) -> Request:
    """Example ESI request for the GetCharactersCharacterIdBlueprints operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCharactersCharacterIdBlueprints",
        path_parameters={"character_id": character_id},
        query_parameters={"page": 1},
        auth_character_id=character_id,
        lang="en",
        json_body=None,
        response_handlers=handlers,
    )


def character_information(
    character_id: int, handlers: list[ResponseHandlerConfig] | None = None
) -> Request:
    """Example ESI request for the GetCharactersCharacterId operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCharactersCharacterId",
        path_parameters={"character_id": character_id},
        query_parameters={},
        auth_character_id=None,
        lang="en",
        json_body=None,
        response_handlers=handlers,
    )


def corporation_blueprints(
    corporation_id: int,
    character_id: int,
    handlers: list[ResponseHandlerConfig] | None = None,
) -> Request:
    """Example ESI request for the GetCorporationsCorporationIdBlueprints operation."""
    handlers = handlers or []
    return Request(
        request_id=uuid4(),
        operation_id="GetCorporationsCorporationIdBlueprints",
        path_parameters={"corporation_id": corporation_id},
        query_parameters={"page": 1},
        auth_character_id=character_id,
        lang="en",
        json_body=None,
        response_handlers=handlers,
    )
