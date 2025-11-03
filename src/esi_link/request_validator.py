"""Request Validator Module.

This module contains functions to validate incoming requests.
"""

from typing import Any, Protocol

from esi_link.helpers import operation_accessors as OA
from esi_link.models import EsiRequest, EsiSchema


class ValidationError(Exception):
    """Exception raised for errors in the ESI request validation."""

    def __init__(self, message: str, request: EsiRequest | None = None) -> None:
        """Initialize the ValidationError with an optional request."""
        super().__init__(message)
        self.request = request


class EsiRequestValidatorProtocol(Protocol):
    """Protocol for validating ESI requests."""

    def validate(self, request: EsiRequest) -> None:
        """Validate the given ESI request.

        Args:
            request (EsiRequest): The request to validate.

        Raises:
            ValidationError: If the request is invalid.
        """
        ...


class SimpleValidator:
    """A simple implementation of the EsiQueryValidatorProtocol that performs basic validation."""

    def __init__(self, esi_schema: EsiSchema) -> None:
        """Initialize the SimpleValidator with the given ESI schema."""
        self._esi_schema = esi_schema

    def validate(self, request: EsiRequest) -> None:
        """Validate the given ESI request.

        Args:
            request (EsiRequest): The request to validate.

        Raises:
            ValidationError: If the request is invalid.
        """
        try:
            self._validate_request(request)
        except ValidationError as ve:
            raise ValidationError(str(ve), request=request) from ve

    def _validate_request(self, request: EsiRequest) -> None:
        """Validate the given ESI request."""
        check_valid_operation_id(
            esi_schema=self._esi_schema, operation_id=request.operation_id
        )
        check_path_parameters(
            esi_schema=self._esi_schema,
            operation_id=request.operation_id,
            request_path_params=request.path_parameters,
        )
        check_query_parameters(
            esi_schema=self._esi_schema,
            operation_id=request.operation_id,
            request_query_params=request.query_parameters,
        )
        check_request_headers(
            esi_schema=self._esi_schema,
            operation_id=request.operation_id,
            request_header_params=request.headers,
        )
        check_request_body_parameters(
            esi_schema=self._esi_schema,
            operation_id=request.operation_id,
            request_body_params=request.request_body,
        )


def check_valid_operation_id(
    esi_schema: EsiSchema,
    operation_id: str,
) -> None:
    """Check if the given operation ID is valid.

    Args:
        esi_schema (EsiSchema): The ESI schema.
        operation_id (str): The operation ID to check.

    Raises:
        ValidationError: If the operation ID is invalid.
    """
    operation = esi_schema.operations.get(operation_id)
    if not operation:
        raise ValidationError(f"Invalid operation ID: {operation_id}")


def check_path_parameters(
    esi_schema: EsiSchema,
    operation_id: str,
    request_path_params: dict[str, str | int | float],
) -> None:
    """Check if the required path parameters are present for the given operation ID.

    Args:
        esi_schema (EsiSchema): The ESI schema.
        operation_id (str): The operation ID.
        request_path_params (dict[str, str | int | float]): A dictionary of path parameters.

    Raises:
        ValidationError: If required path parameters are missing or unrecognized.
    """
    # Get a dict of required path parameters from the spec
    operation = esi_schema.operations.get(operation_id)
    if not operation:
        raise ValidationError(f"Invalid operation ID: {operation_id}")
    required_params = OA.request_path_parameters(operation)

    # Check no extra path parameters are provided in path_params
    if not all(path_param in required_params for path_param in request_path_params):
        raise ValidationError(
            f"Unrecognized path parameters given.:{request_path_params=!r}, {required_params=!r}"
        )

    # Check if all required parameters are present in the provided path_params
    if not all(
        required_param in request_path_params for required_param in required_params
    ):
        raise ValidationError(
            f"Missing required path parameters: {request_path_params=!r}, {required_params=!r}"
        )


def check_query_parameters(
    esi_schema: EsiSchema,
    operation_id: str,
    request_query_params: dict[str, str | int | float],
) -> None:
    """Check if the required query parameters are present for the given operation ID.

    Args:
        esi_schema (EsiSchema): The ESI schema.
        operation_id (str): The operation ID.
        request_query_params (dict[str, str | int | float]): A dictionary of query parameters.

    Raises:
        ValidationError: If required query parameters are missing or unrecognized.
    """
    # Get the list of required query parameters from the spec
    operation = esi_schema.operations.get(operation_id)
    if not operation:
        raise ValidationError(f"Invalid operation ID: {operation_id}")
    possible_params = OA.request_query_parameters(operation)

    # Check no extra query parameters are provided in query_params
    if not all(query_param in possible_params for query_param in request_query_params):
        raise ValidationError(
            f"Unrecognized query parameters given: {request_query_params=!r}, {possible_params=!r}"
        )

    # Check if all required parameters are present in the provided query_params
    for key, value in possible_params.items():
        if value.get("required", False):
            if key not in request_query_params:
                raise ValidationError(
                    f"Missing required query parameters: {request_query_params=!r}, {possible_params=!r}, "
                )


def check_request_headers(
    esi_schema: EsiSchema,
    operation_id: str,
    request_header_params: dict[str, str | int | float],
) -> None:
    """Check if the headers present are allowed for user requests.

    Args:
        esi_schema (EsiSchema): The ESI schema.
        operation_id (str): The operation ID.
        request_header_params (dict[str, str | int | float]): A dictionary of header parameters.

    Raises:
        ValidationError: If required header parameters are missing or unrecognized.
    """
    pass
    # AI gen not checked
    # header verification might be complicated by auth headers, etc.
    # # Get the list of required header parameters from the spec
    # operation = esi_api.indexed_operation(operation_id)
    # possible_params = OA.request_header_parameters(operation)

    # # Check no extra header parameters are provided in header_params
    # if not all(header_param in possible_params for header_param in header_params):
    #     raise ValidationError(
    #         f"Unrecognized header parameters given: {header_params=!r}, {possible_params=!r}"
    #     )

    # # Check if all required parameters are present in the provided header_params
    # for key, value in possible_params.items():
    #     if value.get("required", False):
    #         if key not in header_params:
    #             raise ValidationError(
    #                 f"Missing required header parameters: {header_params=!r}, {possible_params=!r}, "
    #             )


def check_request_body_parameters(
    esi_schema: EsiSchema,
    operation_id: str,
    request_body_params: dict[str, Any],
) -> None:
    """Check if the request body parameters are valid for the given operation ID.

    Args:
        esi_schema (EsiSchema): The ESI schema.
        operation_id (str): The operation ID.
        request_body_params (dict[str, Any]): The request body parameters.

    Raises:
        ValidationError: If the request body parameters are invalid.
    """
    pass
    # AI gen not checked
    # Are body params guaranteed as dicts? lists? other?
    # Also check for missing/present as appropriate.
    # operation = esi_api.indexed_operation(operation_id)
    # if not OA.request_body(operation):
    #     if body_params:
    #         raise ValidationError(
    #             f"Operation {operation_id} does not accept a request body, but body_params were provided."
    #         )
    # else:
    #     # Further validation of body_params against the schema can be added here
    #     pass
