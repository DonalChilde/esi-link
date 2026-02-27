"""Request validation for ESI requests based on an indexed schema."""

import logging

from esi_link.v2.models import (
    EsiRequest,
    HandlerManagerProtocol,
    IndexedEsiSchema,
    IndexedOperation,
    RequestValidatorProtocol,
    ValidationError,
)

logger = logging.getLogger(__name__)


def validate_request_path_params(
    request: EsiRequest, operation: IndexedOperation
) -> None:
    """Validate the request path against the indexed schema.

    only checks for the presence or absence of parameters.
    """
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
    request: EsiRequest, operation: IndexedOperation
) -> None:
    """Validate the request query parameters against the indexed schema.

    This includes checking for required parameters, validating parameter types, and
    ensuring that parameter values conform to any specified constraints (e.g., enums, min/max values).
    """
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


def validate_request_body(request: EsiRequest, operation: IndexedOperation) -> None:
    """Validate the request body against the indexed schema."""
    # TODO implement request body validation based on the operation's requestBody schema
    pass


def validate_request_auth(request: EsiRequest, operation: IndexedOperation) -> None:
    """Validate the request authentication against the indexed schema."""
    if not operation:
        raise ValueError(f"Operation ID {request.operation_id} not found in schema")
    if operation.auth_required and not request.auth_parameters:
        raise ValueError(f"Operation ID {request.operation_id} requires authentication")
    if request.auth_parameters and not operation.auth_required:
        raise ValueError(
            f"Operation ID {request.operation_id} does not require authentication"
        )


class RequestValidator(RequestValidatorProtocol):
    def __init__(
        self, schema: IndexedEsiSchema, handler_manager: HandlerManagerProtocol
    ):
        """Initialize the RequestValidator with the indexed schema and handler manager."""
        self.schema = schema
        self.handler_manager = handler_manager

    def validate(self, request: EsiRequest) -> None:
        """Validate an ESI request against the indexed schema."""
        try:
            if request.operation_id not in self.schema.operations:
                raise ValueError(
                    f"Operation ID {request.operation_id} not found in schema"
                )
            operation = self.schema.operations[request.operation_id]
            validate_request_path_params(request, operation)
            validate_request_query_params(request, operation)
            validate_request_body(request, operation)
            validate_request_auth(request, operation)
            for handler_config in request.response_handlers:
                self.handler_manager.validate_handler_config(handler_config)
        except Exception as e:
            logger.error(
                f"ESI request validation failed: {e}, schema version: {self.schema.version}, request: {request.model_dump_json()}"
            )
            raise ValidationError(
                f"ESI request validation failed: {e}. See logs for details.",
                request,
                self.schema.version,
            ) from e
