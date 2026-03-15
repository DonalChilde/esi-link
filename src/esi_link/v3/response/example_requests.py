"""Example ESI requests for testing and demonstration purposes."""

from uuid import uuid4

from esi_link.models import EsiRequest, HandlerConfig


def simple_save_response(output_dir: str, overwrite: bool = False) -> HandlerConfig:
    """Example HandlerConfig for the SimpleSaveToDiskResponseHandler.

    This config specifies the output directory and whether to overwrite existing files.
    The output_dir can be an absolute path (e.g. "/path/to/output/dir") or a path relative to the current working directory (e.g. "output/dir").
    """
    return HandlerConfig(
        name="esi-link:simple_save_to_disk",
        config={"output_dir": output_dir, "overwrite": overwrite},
    )


def esi_status(handlers: list[HandlerConfig] | None = None) -> EsiRequest:
    """Example ESI request for the /status endpoint."""
    handlers = handlers or []
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetStatus",
        path_parameters={},
        query_parameters={},
        body=None,
        response_handlers=handlers,
    )


def esi_changelog(handlers: list[HandlerConfig] | None = None) -> EsiRequest:
    """Example ESI request for the /meta/changelog endpoint."""
    handlers = handlers or []
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetMetaChangelog",
        path_parameters={},
        query_parameters={},
        body=None,
        response_handlers=handlers,
    )


def market_types_with_active_orders(
    region_id: int = 10000002, handlers: list[HandlerConfig] | None = None
) -> EsiRequest:
    """Example ESI request for the /markets/{region_id}/types/ endpoint with a query parameter."""
    handlers = handlers or []
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdTypes",
        path_parameters={"region_id": region_id},
        query_parameters={"page": 1},
        body=None,
        response_handlers=handlers,
    )
