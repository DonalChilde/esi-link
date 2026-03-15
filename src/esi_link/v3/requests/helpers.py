# from esi_link.v3.models import Response


# def combine_paged_response_strings(first_page: str, paged_strings: list[str]) -> str:
#     """Combine the body text from the original response and the paged responses into a single string."""
#     # This logic assumes that the body of the response is a JSON array of items,
#     # which is true for many ESI endpoints, but may not be universally true.
#     # We may need to make this logic more robust in the future.

#     if first_page.startswith("[") and first_page.endswith("]"):
#         return combine_list_of_array_strings(first_page, paged_strings)
#     else:
#         raise ValueError(
#             "Cannot combine paged response strings: original string is not a JSON array"
#         )


# def combine_list_of_array_strings(first_page: str, paged_strings: list[str]) -> str:
#     """Combine the body text from the original response and the paged responses into a single json string list of items."""
#     fragments: list[str] = []
#     if first_page.startswith("[") and first_page.endswith("]"):
#         fragments.append(first_page[1:-1])  # Remove the brackets
#         for page_num, paged_string in enumerate(paged_strings, start=2):
#             if paged_string.startswith("[") and paged_string.endswith("]"):
#                 fragments.append(paged_string[1:-1])  # Remove the brackets
#             else:
#                 raise ValueError(
#                     f"Cannot combine paged response strings: paged string is not a JSON array: page {page_num}"
#                 )
#         combined_string = f"[{','.join(fragments)}]"  # Add the brackets back
#         return combined_string
#     else:
#         raise ValueError(
#             "Cannot combine paged response strings: original string is not a JSON array"
#         )


# def collect_paged_response_strings(paged_responses: list[Response]) -> list[str]:
#     """Collect the body text from a list of paged responses."""
#     response_strings: list[str] = []
#     for paged_response in paged_responses:
#         page_num = paged_response.runtime_info.additional_query_params.get(
#             "page", "unknown"
#         )
#         if paged_response.http_response is None:
#             raise ValueError(
#                 f"Cannot collect response string from a paged response with no HTTP response: page {page_num}"
#             )
#         if not paged_response.http_response.body_text:
#             raise ValueError(
#                 f"Cannot collect response string from a paged response with no body text: page {page_num}"
#             )
#         response_strings.append(paged_response.http_response.body_text)
#     return response_strings


# def check_for_valid_paged_reponses(
#     response: Response, paged_responses: list[Response]
# ) -> None:
#     """Check that the paged responses are valid and can be combined with the original response."""
#     if response.http_response is None:
#         raise ValueError(
#             "Cannot check paged responses for a response with no HTTP response"
#         )
#     for paged_response in paged_responses:
#         page_num = paged_response.runtime_info.additional_query_params.get(
#             "page", "unknown"
#         )
#         if paged_response.http_response is None:
#             raise ValueError(
#                 f"Invalid paged response: page {page_num} has no HTTP response"
#             )
#         if paged_response.http_response.status_code != 200:
#             logger.error(
#                 f"Received unexpected status code {paged_response.http_response.status_code} "
#                 f"for paged response to request {response.request.request_id} page {page_num}"
#                 f"\n{paged_response.model_dump_json(indent=2)}"
#             )
#             raise ValueError(
#                 f"Invalid paged response: page {page_num} has an unexpected status code {paged_response.http_response.status_code}"
#             )
#         if (
#             paged_response.http_response.last_modified
#             != response.http_response.last_modified
#         ):
#             raise ValueError(
#                 f"Invalid paged response: page {page_num} has a different Last-Modified header than the original response"
#             )
