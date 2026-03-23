"""Detailed File Saver Response Handler for ESI Link."""

import json

from esi_link.handlers.response.standard_file_saver import (
    StandardFileSaverResponseHandler,
)
from esi_link.models_and_protocols import Response


class DetailedFileSaverResponseHandler(StandardFileSaverResponseHandler):
    """Response Handler that saves the response to a templated file path.

    Saves the response as a json dict with the following keys:
    - All the fields from the original Request, plus the following additional fields:
    - response_data: the data from the http response, if available, otherwise None
    - response_date: the date of the http response, if available, otherwise "NO_RESPONSE_DATE"

    If there are any errors in the response (network exceptions, http response is None, etc),
    then saves the entire response as json instead, to capture the error information. In
    this case, the file name will still be generated from the template, but will have the
    suffix "_WITH_ERRORS" added to it, before the file extension.
    """

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
