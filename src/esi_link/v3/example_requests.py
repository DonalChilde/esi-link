"""Example ESI requests for testing and demonstration purposes."""

from pathlib import Path
from uuid import uuid4

from esi_link.v3.models_and_protocols import Request, ResponseHandlerConfig


def simple_save_response(
    output_dir: Path, overwrite: bool = False
) -> ResponseHandlerConfig:
    """Example ResponseHandlerConfig for the SimpleSaveToDiskResponseHandler.

    This config specifies the output directory and whether to overwrite existing files.
    The output_dir can be relative to the user's home directory (e.g. "~/path/to/output/dir")
    or a path relative to the current working directory (e.g. "output/dir").
    """
    return ResponseHandlerConfig(
        name="esi-link:simple_save_to_disk",
        config={"output_dir": str(output_dir), "overwrite": overwrite},
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
