from uuid import uuid4

from esi_link.v2.request_runtime_info import EsiRequest


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
