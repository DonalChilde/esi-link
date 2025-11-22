"""Factory functions for creating EsiRequest objects for various ESI operations.

This is not ment to be a complete list of all ESI operations, just some common ones that
are frequently used.
"""

from uuid import uuid4

from esi_link.models import EsiRequest


def status() -> EsiRequest:
    """Create an EsiRequest for the GetStatus operation.

    This function constructs an EsiRequest object specifically for the
    "GetStatus" operation of the EVE Swagger Interface (ESI). The request
    is initialized with a unique request ID.

    Returns:
        EsiRequest: An instance of EsiRequest configured for the GetStatus operation.
    """
    return EsiRequest(request_id=uuid4(), operation_id="GetStatus")
