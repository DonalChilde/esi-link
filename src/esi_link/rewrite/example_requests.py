"""Example requests for testing and documentation purposes."""

from uuid import uuid4

from esi_link.rewrite.request.models import Request, RequestGroup


def api_status() -> Request:
    """Example request for the EVE ESI api status endpoint."""
    return Request(
        request_id=uuid4(),
        operation_id="GetMetaStatus",
        description="Example request for the EVE ESI api status endpoint.",
    )


def server_status() -> Request:
    """Example request for the EVE ESI server status endpoint."""
    return Request(
        request_id=uuid4(),
        operation_id="GetStatus",
        description="Example request for the EVE ESI server status endpoint.",
    )


def status_group() -> RequestGroup:
    """Example request group for the EVE ESI status endpoints."""
    api_status_request = api_status()
    server_status_request = server_status()
    return RequestGroup(
        group_id=uuid4(),
        description="Example request group for the EVE ESI status endpoints.",
        requests={
            api_status_request.request_id: api_status_request,
            server_status_request.request_id: server_status_request,
        },
    )
