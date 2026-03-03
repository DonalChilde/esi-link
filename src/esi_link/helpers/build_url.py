"""Build full URLs for ESI requests based on the ESI schema."""

from copy import deepcopy


def build_url(
    path_parameters: dict[str, str | int | float],
    query_parameters: dict[str, str | int | float],
    base_url: str,
    path_template: str,
    additional_query_params: dict[str, str] | None = None,
) -> str:
    """Build the full URL for an ESI request using the ESI schema.

    Use addtional_query_params to include query parameters that aren't user settable,
    such as pagination parameters and compatibility date.

    Args:
        path_parameters: The path parameters for the ESI request.
        query_parameters: The query parameters for the ESI request.
        base_url: The base URL for the ESI request.
        path_template: The path template for the ESI request.
        additional_query_params: Optional dictionary of additional query parameters to include in the URL.

    Returns:
        The full URL as a string.
    """
    path = path_template.format(**path_parameters)
    resolved_url = f"{base_url.strip('/')}/{path.strip('/')}"
    # Construct the query string from the query parameters
    if additional_query_params:
        # Avoid mutating the original query parameters
        query_parameters = deepcopy(query_parameters)
        query_parameters.update(additional_query_params)
    # Sort keys so URL is stable regardless of dict insertion order
    query_items = sorted(query_parameters.items(), key=lambda kv: kv[0])
    query_string = "&".join([f"{key}={value}" for key, value in query_items])
    # Combine the path and query string into the final URL
    return f"{resolved_url}?{query_string}" if query_string else resolved_url
