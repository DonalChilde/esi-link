import json
from typing import Any

from esi_link.esi_client.models import QueryResponse


def response_to_json(response: QueryResponse) -> dict[str, Any]:
    """Convert a QueryResponse.text to a JSON-serializable dictionary.

    NOTE: This function assumes that the response text is a valid JSON string.
    NOTE: This also assumes that the paged_text is a dict.
    FIXME: This function currently does not handle non-JSON responses gracefully.
    FIXME: Needs to handle json that might be the error report for a bad request.
    """

    try:
        first_page_data = json.loads(response.text) if response.text else {}
    except json.JSONDecodeError:
        first_page_data: dict[str, Any] = {}
    if response.paged_text:
        data_list: list[dict[str, Any]] = []
        for page in response.paged_text:
            try:
                page_data = json.loads(page) if page else {}
            except json.JSONDecodeError:
                page_data: dict[str, Any] = {}
            data_list.append(page_data)
        first_page_data.update(
            {key: value for d in data_list for key, value in d.items()}
        )
    return first_page_data
