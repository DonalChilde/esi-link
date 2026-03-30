import json
from typing import Any

from esi_link.handlers.errors import HandlerValidationError
from esi_link.models_and_protocols import Response, ResponseData, ResponseHandlerConfig


def check_available_keys(
    config: ResponseHandlerConfig, required_keys: set[str]
) -> None:
    """Check the ResponseHandlerConfig for the required keys and their types."""
    keys = set(config.config.keys())
    missing_keys = required_keys - keys
    if missing_keys:
        raise HandlerValidationError(
            f"Missing required config keys: {missing_keys}", config=config.model_dump()
        )
    extra_keys = keys - required_keys
    if extra_keys:
        raise HandlerValidationError(
            f"Extra config keys not used by handler: {extra_keys}",
            config=config.model_dump(),
        )


def make_response_details(response: Response) -> dict[str, Any]:
    """Get the details of the response for use in filename tokens."""
    request_detail = response.request.model_dump(mode="json")
    request_detail["response_date"] = (
        response.http_response.date
        if response.http_response and response.http_response.date
        else "NO_RESPONSE_DATE"
    )
    request_detail["response_data"] = (
        json.loads(response.http_response.body_text) if response.http_response else None
    )

    return request_detail


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
        data=response_data,
    )
