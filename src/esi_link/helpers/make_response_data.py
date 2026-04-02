"""Helper function to make a ResponseData object from a Response, including the http response data if available."""

import json

from esi_link.models_and_protocols import Response, ResponseData


def make_response_data(response: Response) -> ResponseData:
    """Make a ResponseData object from the Response, including the http response data if available."""
    if response.http_response is None:
        raise ValueError(
            f"Response {response.request.request_id} http_response is None, cannot make ResponseData"
        )
    try:
        response_data = json.loads(response.http_response.body_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Response {response.request.request_id} http_response body_text is not valid JSON, cannot make ResponseData"
        ) from e
    response_date = (
        response.http_response.date
        if response.http_response.date
        else "NO_RESPONSE_DATE"
    )
    return ResponseData(
        request=response.request,
        response_date=response_date,
        received_at=response.http_response.received_at,
        data=response_data,
    )
