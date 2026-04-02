"""ResponseData File Saver Response Handler for ESI Link."""

import json

from esi_link.handlers.response.standard_file_saver import (
    StandardFileSaverResponseHandler,
)
from esi_link.helpers.make_response_data import make_response_data
from esi_link.models_and_protocols import Response


class ResponseDataFileSaverResponseHandler(StandardFileSaverResponseHandler):
    """Response Handler that saves the response to a templated file path.

    Saves the response data as a json dict with the following keys:
    - request: the original Request object, as a dict
    - data: the data from the http response
    - response_date: the date of the http response, if available, otherwise "NO_RESPONSE_DATE"

    If there are any errors in the response (network exceptions, http response is None, etc),
    then saves the entire response as json instead, to capture the error information. In
    this case, the file name will still be generated from the template, but will have the
    suffix "_WITH_ERRORS" added to it, before the file extension.
    """

    name = "esi-link:response_data_file_saver"

    def get_text_to_save(self, response: Response) -> str:
        """Get the text to save for the response, including debug information."""
        if self._has_errors(response):
            return response.model_dump_json(indent=2)
        response_data = make_response_data(response)
        return json.dumps(response_data.model_dump(), indent=2)
