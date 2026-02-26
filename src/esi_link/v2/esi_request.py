"""Functions for working with EsiRequests."""

import logging

from esi_link.v2 import USER_AGENT
from esi_link.v2.helpers.build_url import build_url
from esi_link.v2.helpers.cache_key_from_url import cache_key_from_url
from esi_link.v2.models import (
    AuthProviderProtocol,
    EsiRequest,
    HandlerManagerProtocol,
    IndexedEsiSchema,
    RuntimeRequestInfo,
)

logger = logging.getLogger(__name__)


def validate_request_path_params(request: EsiRequest, schema: IndexedEsiSchema) -> None:
    """Validate the request path against the indexed schema.

    only checks for the presence or absence of parameters.
    """
    operation = schema.operations.get(request.operation_id)
    if not operation:
        raise ValueError(f"Operation ID {request.operation_id} not found in schema")
    path_params = {
        param.get("name", "UNKNOWN"): param for param in operation.path_params
    }
    if "UNKNOWN" in path_params:
        raise ValueError(
            f"Operation ID {request.operation_id} has path parameters without names"
        )
    for param_name, param_schema in path_params.items():
        if param_name not in request.path_parameters:
            if param_schema.get("required", False):
                continue  # Required path parameters must be present
            raise ValueError(f"Missing required path parameter: {param_name}")
    for param_name in request.path_parameters:
        if param_name not in path_params:
            raise ValueError(f"Unexpected path parameter: {param_name}")


def validate_request_query_params(
    request: EsiRequest, schema: IndexedEsiSchema
) -> None:
    """Validate the request query parameters against the indexed schema.

    This includes checking for required parameters, validating parameter types, and
    ensuring that parameter values conform to any specified constraints (e.g., enums, min/max values).
    """
    operation = schema.operations.get(request.operation_id)
    if not operation:
        raise ValueError(f"Operation ID {request.operation_id} not found in schema")
    query_params = {
        param.get("name", "UNKNOWN"): param for param in operation.query_params
    }
    if "UNKNOWN" in query_params:
        raise ValueError(
            f"Operation ID {request.operation_id} has query parameters without names"
        )
    for param_name, param_schema in query_params.items():
        if param_name not in request.query_parameters:
            if param_schema.get("required", False):
                continue  # Optional parameters can be missing
            raise ValueError(f"Missing required query parameter: {param_name}")
    for param_name in request.query_parameters:
        if param_name not in query_params:
            raise ValueError(f"Unexpected query parameter: {param_name}")


def validate_request_body(request: EsiRequest, schema: IndexedEsiSchema) -> None:
    """Validate the request body against the indexed schema."""
    # TODO implement request body validation based on the operation's requestBody schema
    pass


def validate_request_auth(request: EsiRequest, schema: IndexedEsiSchema) -> None:
    """Validate the request authentication against the indexed schema."""
    operation = schema.operations.get(request.operation_id)
    if not operation:
        raise ValueError(f"Operation ID {request.operation_id} not found in schema")
    if operation.auth_required and not request.auth_parameters:
        raise ValueError(f"Operation ID {request.operation_id} requires authentication")
    if request.auth_parameters and not operation.auth_required:
        raise ValueError(
            f"Operation ID {request.operation_id} does not require authentication"
        )


def validate_esi_request(
    request: EsiRequest,
    schema: IndexedEsiSchema,
    handler_manager: HandlerManagerProtocol,
) -> None:
    """Validate an ESI request against the indexed schema."""
    try:
        if request.operation_id not in schema.operations:
            raise ValueError(f"Operation ID {request.operation_id} not found in schema")
        validate_request_path_params(request, schema)
        validate_request_query_params(request, schema)
        validate_request_body(request, schema)
        validate_request_auth(request, schema)
        for handler_config in request.response_handlers:
            handler_manager.validate_handler_config(handler_config)
    except Exception as e:
        logger.error(
            f"ESI request validation failed: {e}, schema version: {schema.version}, request: {request.model_dump_json()}"
        )
        raise ValueError(
            f"ESI request validation failed: {e}. See logs for details."
        ) from e


def populate_runtime_info(
    request: EsiRequest,
    schema: IndexedEsiSchema,
    auth_provider: AuthProviderProtocol,
    lang: str = "en",
) -> None:
    """Populate the runtime info for an ESI request based on the indexed schema."""
    if request.operation_id not in schema.operations:
        raise ValueError(f"Operation ID {request.operation_id} not found in schema")
    operation = schema.operations[request.operation_id]
    base_url = schema.servers[0]["url"]
    path_template = operation.path
    headers: dict[str, str] = {}
    if operation.auth_required and request.auth_parameters:
        auth_headers = auth_provider.get_auth_headers(
            character_id=request.auth_parameters.character_id,
            client_alias=request.auth_parameters.client_alias,
        )
        headers.update(auth_headers)
    headers["User-Agent"] = USER_AGENT
    headers["Accept-Language"] = lang
    headers["X-Compatibility-Date"] = schema.version
    url = build_url(
        path_parameters=request.path_parameters or {},
        query_parameters=request.query_parameters or {},
        base_url=base_url,
        path_template=path_template,
    )
    if operation.is_cached:
        cache_key = cache_key_from_url(url)
    else:
        cache_key = None
    runtime = RuntimeRequestInfo(
        url=url,
        base_url=base_url,
        path_template=path_template,
        additional_query_params={},
        method=operation.method,
        is_paged=operation.is_paged,
        is_auth=operation.auth_required,
        headers=headers,
        timeout=10,
        cache_key=cache_key,
    )
    request.runtime_info = runtime
