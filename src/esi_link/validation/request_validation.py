"""Request validation for ESI Link.

Validate a request against the indexed ESI schema, including path parameters, query parameters,
request body, and authentication requirements.

An example of the schema for the parameters of a request.
```json
{
    "parameters": [
        {
            "description": "The ID of the character",
            "in": "path",
            "name": "character_id",
            "required": true,
            "schema": {
                "examples": [90000001],
                "format": "int64",
                "type": "integer",
                "x-common-model": "true",
            },
        },
        {
            "in": "query",
            "name": "labels",
            "schema": {
                "description": "Fetch only mails that match one or more of the given labels",
                "items": {"format": "int64", "type": "integer"},
                "maxItems": 25,
                "minItems": 1,
                "type": "array",
                "uniqueItems": true,
            },
        },
        {
            "in": "query",
            "name": "last_mail_id",
            "schema": {
                "description": "List only mail with an ID lower than the given ID, if present",
                "format": "int64",
                "type": "integer",
            },
        },
        {
            "description": "The language to use for the response.",
            "in": "header",
            "name": "Accept-Language",
            "schema": {
                "default": "en",
                "enum": ["en", "de", "fr", "ja", "ru", "zh", "ko", "es"],
                "type": "string",
            },
        },
        {
            "description": "The ETag of the previous request. A 304 will be returned if this matches the current ETag.",
            "in": "header",
            "name": "If-None-Match",
            "schema": {"type": "string"},
        },
        {
            "description": "The compatibility date for the request.",
            "in": "header",
            "name": "X-Compatibility-Date",
            "required": true,
            "schema": {"enum": ["2025-12-16"], "format": "date", "type": "string"},
        },
        {
            "description": "The tenant ID for the request.",
            "example": "",
            "in": "header",
            "name": "X-Tenant",
            "schema": {"default": "tranquility", "type": "string"},
        },
        {
            "description": "The date the resource was last modified. A 304 will be returned if the resource has not been modified since this date.",
            "in": "header",
            "name": "If-Modified-Since",
            "schema": {"type": "string"},
        },
    ]
}
```
"""

import logging

from esi_link.esi_auth.protocols import AuthProviderProtocol
from esi_link.models_and_protocols import (
    EsiSchema,
    Request,
    RequestValidatorProtocol,
    # ResponseHandlerManagerProtocol,
    SchemaOperation,
)
from esi_link.validation.errors import RequestValidationError

logger = logging.getLogger(__name__)

# TODO add samples of the schema structure to the docstrings of the validation functions for clarity


class RequestValidator(RequestValidatorProtocol):
    def __init__(
        self,
        schema: EsiSchema,
        # response_handler_manager: ResponseHandlerManagerProtocol,
        auth_provider: AuthProviderProtocol,
    ) -> None:
        """Initialize the RequestValidator.

        Args:
            schema: The EsiSchema to validate against.
            response_handler_manager: The response handler manager to validate response handler configs against.
            auth_provider: The authentication provider to validate request authentication against.
        """
        self.schema = schema
        # self.response_handler_manager = response_handler_manager
        self.auth_provider = auth_provider

    async def __call__(self, request: Request) -> None:
        """Validate an ESI request against the EsiSchema."""
        try:
            if request.operation_id not in self.schema.operations:
                raise RequestValidationError(
                    f"Operation ID {request.operation_id} not found in schema",
                    request,
                )
            operation = self.schema.operations[request.operation_id]
            validate_request_path_params(request, operation)
            validate_request_query_params(request, operation)
            validate_request_body(request, operation)
            await validate_request_auth(request, operation, self.auth_provider)
            # for handler_config in request.response_handlers:
            #     self.response_handler_manager.validate_handler_config(handler_config)
        except RequestValidationError:
            raise
        except Exception as e:
            logger.error(
                f"ESI request validation failed: {e}, schema version: {self.schema.version}, request: {request.model_dump_json()}"
            )
            raise RequestValidationError(
                f"ESI request validation failed: {e}. See logs for details.",
                request,
            ) from e


def validate_request_path_params(request: Request, operation: SchemaOperation) -> None:
    """Validate the request path against the EsiSchema operation.

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


def validate_request_query_params(request: Request, operation: SchemaOperation) -> None:
    """Validate the request query parameters against the EsiSchema operation.

    This includes checking for required parameters, validating parameter types, and
    ensuring that parameter values conform to any specified constraints (e.g., enums, min/max values).
    """
    query_params = {
        param.get("name", "UNKNOWN"): param for param in operation.query_params
    }
    if "UNKNOWN" in query_params:
        raise ValueError(
            f"Operation ID {request.operation_id} has query parameters without names"
        )
    for param_name, param_schema in query_params.items():
        if param_name not in request.query_parameters:
            required = param_schema.get("required", False)
            if not required:
                continue  # Optional parameters can be missing
            raise ValueError(f"Missing required query parameter: {param_name}")
    for param_name in request.query_parameters:
        if param_name not in query_params:
            raise ValueError(f"Unexpected query parameter: {param_name}")


def validate_request_body(request: Request, operation: SchemaOperation) -> None:
    """Validate the request body against the EsiSchema operation."""
    # TODO implement request body validation based on the operation's requestBody schema
    pass


async def validate_request_auth(
    request: Request, operation: SchemaOperation, auth_provider: AuthProviderProtocol
) -> None:
    """Validate the request authentication against the EsiSchema operation."""
    if not operation:
        raise ValueError(f"Operation ID {request.operation_id} not found in schema")
    if operation.auth_required and not request.auth_character_id:
        raise ValueError(f"Operation ID {request.operation_id} requires authentication")
    if request.auth_character_id and not operation.auth_required:
        raise ValueError(
            f"Operation ID {request.operation_id} does not require authentication"
        )
    if request.auth_character_id:
        available_characters = await auth_provider.available_characters()
        if request.auth_character_id not in available_characters:
            raise ValueError(
                f"Authentication information for character ID {request.auth_character_id} is not available"
            )
