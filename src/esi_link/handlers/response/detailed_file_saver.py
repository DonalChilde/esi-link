"""Detailed File Saver Response Handler for ESI Link."""

import json

from esi_link.handlers.response.standard_file_saver import (
    StandardFileSaverResponseHandler,
)
from esi_link.models_and_protocols import Response


class DetailedFileSaverResponseHandler(StandardFileSaverResponseHandler):
    """Response Handler that saves the response to a templated file path, with additional debug information."""

    name = "esi-link:detailed_file_saver"

    def get_text_to_save(self, response: Response) -> str:
        """Get the text to save for the response, including debug information."""
        if self._has_errors(response):
            return response.model_dump_json(indent=2)
        request = response.request.model_dump(mode="json")
        request["response_data"] = (
            json.loads(response.http_response.body_text)
            if response.http_response
            else None
        )
        request["response_date"] = (
            response.http_response.date
            if response.http_response and response.http_response.date
            else "NO_RESPONSE_DATE"
        )
        return json.dumps(request, indent=2)
