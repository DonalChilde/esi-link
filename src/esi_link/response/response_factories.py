"""Factory methods to transform responses."""

import json
from dataclasses import asdict
from uuid import UUID

from esi_link.response.models import (
    ResponseData,
    ResponseDataGroup,
    ResponseGroup,
)


def response_group_to_response_data(
    response_group: ResponseGroup,
) -> dict[UUID, ResponseData]:
    """Convert a ResponseGroup to a dictionary of ResponseData."""
    request_group = response_group.request_group
    responses_data = {
        request_id: ResponseData(
            request=request_group.requests[request_id],
            data=json.loads(response.http_response.text),
            metrics=asdict(response.metrics),
        )
        for request_id, response in response_group.responses.items()
    }
    return responses_data


def response_group_to_response_data_group(
    response_group: ResponseGroup,
) -> ResponseDataGroup:
    """Convert a ResponseGroup to a ResponseDataGroup."""
    responses_data = response_group_to_response_data(response_group)
    return ResponseDataGroup(responses=responses_data)
