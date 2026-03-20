"""Example ESI requests for testing and demonstration purposes."""

from pathlib import Path
from uuid import uuid4

from esi_link.models_and_protocols import Request, ResponseHandlerConfig


def debug_file_response(
    output_dir: Path, overwrite: bool = False
) -> ResponseHandlerConfig:
    """Example ResponseHandlerConfig for the DebugFileSaverResponseHandler.

    This config specifies the output directory and whether to overwrite existing files.
    The output_dir can be relative to the user's home directory (e.g. "~/path/to/output/dir")
    or a path relative to the current working directory (e.g. "output/dir").
    """
    return ResponseHandlerConfig(
        name="esi-link:debug_file_saver",
        config={
            "output_dir": str(output_dir),
            "filename_template": "${iso_response_date}-${operation_id}-${request_id}-DEBUG.json",
            "overwrite": overwrite,
        },
    )


def standard_file_response(
    output_dir: Path,
    filename_template: str = "${iso_response_date}-${operation_id}-${request_id}-STANDARD.json",
    overwrite: bool = False,
) -> ResponseHandlerConfig:
    """Example ResponseHandlerConfig for the StandardFileSaverResponseHandler.

    This config specifies the output directory, filename template, and whether to overwrite existing files.
    The output_dir can be relative to the user's home directory (e.g. "~/path/to/output/dir")
    or a path relative to the current working directory (e.g. "output/dir").
    The filename_template can include tokens that will be filled in with values from the response.
    For example, a template of "${iso_response_date}-${operation_id}-${request_id}-STANDARD.json" would create files like "2024-06-01T12_34_56-GetStatus-1234-STANDARD.json".
    """
    return ResponseHandlerConfig(
        name="esi-link:standard_file_saver",
        config={
            "output_dir": str(output_dir),
            "filename_template": filename_template,
            "overwrite": overwrite,
        },
    )


def detailed_file_response(
    output_dir: Path,
    filename_template: str = "${iso_response_date}-${operation_id}-${request_id}-DETAILED.json",
    overwrite: bool = False,
) -> ResponseHandlerConfig:
    """Example ResponseHandlerConfig for the DetailedFileSaverResponseHandler.

    This config specifies the output directory, filename template, and whether to overwrite existing files.
    The output_dir can be relative to the user's home directory (e.g. "~/path/to/output/dir")
    or a path relative to the current working directory (e.g. "output/dir").
    The filename_template can include tokens that will be filled in with values from the response.
    For example, a template of "${iso_response_date}-${operation_id}-${request_id}-DETAILED.json" would create files like "2024-06-01T12_34_56-GetStatus-1234-DETAILED.json".
    """
    return ResponseHandlerConfig(
        name="esi-link:detailed_file_saver",
        config={
            "output_dir": str(output_dir),
            "filename_template": filename_template,
            "overwrite": overwrite,
        },
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
