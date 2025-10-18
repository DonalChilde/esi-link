from esi_link.models import EsiLinkError, EsiRequest, EsiSchema


def build_url(
    esi_request: EsiRequest,
    esi_schema: EsiSchema,
    base_url: str = "",
) -> str:
    """Build the full URL for an ESI request using the ESI schema.

    Args:
        esi_request: The EsiRequest instance containing the operation ID and parameters.
        esi_schema: The EsiSchema instance containing the OpenAPI schema.

    Returns:
        The full URL as a string.
    """
    operation = esi_schema.operations.get(esi_request.operation_id)
    base_url = base_url or esi_schema.servers[0]["url"]
    if not operation:
        raise EsiLinkError(f"Operation ID not found: {esi_request.operation_id}")
    path_params = esi_request.path_parameters or {}
    query_params = esi_request.query_parameters or {}
    path_template = operation.path
    path = path_template.format(**path_params)
    resolved_url = f"{base_url.strip('/')}/{path.strip('/')}"
    # Construct the query string from the query parameters
    # Sort keys so URL is stable regardless of dict insertion order
    query_items = sorted(query_params.items(), key=lambda kv: kv[0])
    query_string = "&".join([f"{key}={value}" for key, value in query_items])
    # Combine the path and query string into the final URL
    return f"{resolved_url}?{query_string}" if query_string else resolved_url
