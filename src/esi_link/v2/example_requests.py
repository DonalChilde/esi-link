from uuid import uuid4

from esi_link.v2.esi_request import EsiRequest


def esi_status() -> EsiRequest:
    """Example ESI request for the /status endpoint."""
    return EsiRequest(
        request_id=uuid4(),
        operation_id="get_status",
        path_parameters={},
        query_parameters={},
        body=None,
        response_handlers=[],
    )
