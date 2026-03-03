"""Example ESI requests for testing and demonstration purposes."""

from uuid import uuid4

from esi_link.runtime_request_generator import EsiRequest


def esi_status() -> EsiRequest:
    """Example ESI request for the /status endpoint."""
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetStatus",
        path_parameters={},
        query_parameters={},
        body=None,
        response_handlers=[],
    )


def esi_changelog() -> EsiRequest:
    """Example ESI request for the /meta/changelog endpoint."""
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetMetaChangelog",
        path_parameters={},
        query_parameters={},
        body=None,
        response_handlers=[],
    )


def market_types_with_active_orders(region_id: int = 10000002) -> EsiRequest:
    """Example ESI request for the /markets/{region_id}/types/ endpoint with a query parameter."""
    return EsiRequest(
        request_id=uuid4(),
        operation_id="GetMarketsRegionIdTypes",
        path_parameters={"region_id": region_id},
        query_parameters={"page": 1},
        body=None,
        response_handlers=[],
    )
