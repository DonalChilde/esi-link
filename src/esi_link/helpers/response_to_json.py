import json
import logging
from copy import deepcopy
from typing import Any

from esi_link.esi_client.models import (
    EsiQuery,
    EsiQueryResult,
    QueryResponse,
    QueryResponseResult,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def query_to_result(query: EsiQuery) -> EsiQueryResult:
    """Convert an EsiQuery with a QueryResponse to EsiQueryResult.

    This is useful for serializing the query to JSON for storage or transmission.
    Args:
        query (EsiQuery): The EsiQuery to convert.
    Returns:
        EsiQueryResult: A new EsiQueryResult with the response converted to QueryResponseResult.
    Raises:
        ValueError: If the query.response is None.

    """
    if query.response is None:
        raise ValueError("query.response is None, cannot convert to JSON.")

    json_data = response_to_json(query.response)
    query_json = EsiQueryResult(
        query_id=query.query_id,
        operation_id=query.operation_id,
        path_parameters=deepcopy(query.path_parameters),
        query_parameters=deepcopy(query.query_parameters),
        request_body=deepcopy(query.request_body),
        headers=deepcopy(query.headers),
        response=QueryResponseResult(
            status_code=query.response.status_code,
            status_reason=query.response.status_reason,
            real_url=query.response.real_url,
            data=json_data,
            headers=deepcopy(query.response.headers),
            completed_on=query.response.completed_on,
        ),
    )
    return query_json


def response_to_json(response: QueryResponse) -> Any:
    """Convert a QueryResponse.text to a JSON-serializable object.

    Args:
        response (QueryResponse): The QueryResponse to convert.
    Returns:
        Any: The JSON-serializable object.
    Raises:
        json.JSONDecodeError: If the response.text or any of the response.paged_text
            cannot be decoded as JSON.
        TypeError: If the response.text is not a list when response.paged_text is present
            or if any of the response.paged_text items are not lists.

    FIXME: Needs to handle json that might be the error report for a bad request.
    """
    try:
        json_response = json.loads(response.text) if response.text else None
    except json.JSONDecodeError as e:
        logger.warning("Failed to decode JSON from response.text %r", response)
        raise e from e
    if response.paged_text:
        if not isinstance(json_response, list):
            # FIXME raise EsiLink custom error here
            msg = f"Expected response.text to be a list when paged_text is present, got {type(json_response)}"
            logger.warning(msg)
            raise TypeError(msg)
        for page in response.paged_text:
            try:
                page_data = json.loads(page) if page else None
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to decode JSON from response.paged_text %r", response
                )
                raise e from e
            if not isinstance(page_data, list):
                # FIXME raise EsiLink custom error here
                msg = f"Expected each page in response.paged_text to be a list, got {type(page_data)}"
                logger.warning(msg)
                raise TypeError(msg)
            json_response.extend(page_data)  # type: ignore
    return json_response  # type: ignore
