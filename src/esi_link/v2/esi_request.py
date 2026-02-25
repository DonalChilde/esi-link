from esi_link.v2.models import EsiRequest, HandlerManagerProtocol, IndexedEsiSchema


def validate_request_path_params(request: EsiRequest, schema: IndexedEsiSchema) -> None:
    """Validate the request path against the indexed schema."""
    ...


def validate_request_query_params(
    request: EsiRequest, schema: IndexedEsiSchema
) -> None:
    """Validate the request query parameters against the indexed schema."""
    ...


def validate_request_body(request: EsiRequest, schema: IndexedEsiSchema) -> None:
    """Validate the request body against the indexed schema."""
    ...


def validate_request_auth(request: EsiRequest, schema: IndexedEsiSchema) -> None:
    """Validate the request authentication against the indexed schema."""
    ...


def validate_esi_request(
    request: EsiRequest,
    schema: IndexedEsiSchema,
    handler_manager: HandlerManagerProtocol,
) -> None:
    """Validate an ESI request against the indexed schema."""
    if request.operation_id not in schema.operations:
        raise ValueError(f"Operation ID {request.operation_id} not found in schema")
    validate_request_path_params(request, schema)
    validate_request_query_params(request, schema)
    validate_request_body(request, schema)
    validate_request_auth(request, schema)
    for handler_config in request.response_handlers:
        handler_manager.validate_handler_config(handler_config)


def populate_runtime_info(request: EsiRequest, schema: IndexedEsiSchema) -> None:
    """Populate the runtime info for an ESI request based on the indexed schema."""
    if request.operation_id not in schema.operations:
        raise ValueError(f"Operation ID {request.operation_id} not found in schema")
    operation = schema.operations[request.operation_id]
    ...
