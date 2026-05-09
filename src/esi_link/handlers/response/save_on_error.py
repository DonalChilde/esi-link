# from esi_link.handlers.response.standard_file_saver import (
#     StandardFileSaverResponseHandler,
# )
# from esi_link.models_and_protocols import Response


# class ErrorOnlyFileSaverResponseHandler(StandardFileSaverResponseHandler):
#     """Response Handler that saves the response to a templated file path.

#     If errors are present, saves the entire response as json, including all fields and
#     any exception messages, to capture all available information for debugging purposes.

#     If there are any errors in the response (network exceptions, http response is None, etc),
#     the file name will still be generated from the template, but will have the
#     suffix "_WITH_ERRORS" added to it, before the file extension.
#     """

#     name = "esi-link:error_only_file_saver"

#     async def handle_response(self, response: Response) -> Response:
#         """Handle the response by saving it to a templated file path."""
#         if self._has_errors(response):
#             output_file_path = self.get_output_path(response)
#             text_to_save = self.get_text_to_save(response)
#             self.save_file(output_file_path, text_to_save)
#         return response

#     def get_text_to_save(self, response: Response) -> str:
#         """Get the text to save for the response, including debug information."""
#         text = response.model_dump_json(indent=2)
#         return text
