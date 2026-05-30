"""Factory methods to transform responses."""

import json

from esi_link.rewrite.response.models import (
    GroupResponseData,
    Response,
    ResponseData,
    ResponseGroup,
)


def response_to_response_data(response: Response) -> ResponseData:
    """Convert a Response to a ResponseData."""
    return ResponseData(
        request=response.runtime_request.validated_request.original_request,
        data=json.loads(response.http_response.text),
    )
