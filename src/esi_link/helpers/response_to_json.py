import json
import logging
from typing import Any

from esi_link.esi_client.models import QueryResponse

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def response_to_json(response: QueryResponse) -> Any:
    """Convert a QueryResponse.text to a JSON-serializable object.

    NOTE: This function assumes that the response text is a valid JSON string.
    NOTE: This also assumes that the paged_text is a list.
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
            json_response.extend(page_data)
    return json_response
