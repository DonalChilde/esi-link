from typing import Any, Protocol

from esi_link.esi_schema import operation_accessors as OA
from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol

from .models import EsiQuery


class ValidationError(Exception):
    """Exception raised for errors in the ESI query validation."""

    pass


class EsiQueryValidatorProtocol(Protocol):
    """Protocol for validating ESI queries."""

    def validate(self, query: EsiQuery) -> None:
        """Validate the given ESI query.

        Args:
            query (EsiQuery): The query to validate.

        RRaises:
            ValidationError: If the query is invalid.
        """
        ...


class SimpleValidator:
    """A simple implementation of the EsiQueryValidatorProtocol that performs basic validation."""

    def __init__(self, esi_api: EsiApiProtocol) -> None:
        self._esi_api = esi_api

    def validate(self, query: EsiQuery) -> None:
        """Validate the given ESI query.

        Args:
            query (EsiQuery): The query to validate.

        Raises:
            ValidationError: If the query is invalid.
        """
        check_valid_operation_id(esi_api=self._esi_api, operation_id=query.operation_id)
        check_path_parameters(
            esi_api=self._esi_api,
            operation_id=query.operation_id,
            path_params=query.path_parameters,
        )
        check_query_parameters(
            esi_api=self._esi_api,
            operation_id=query.operation_id,
            query_params=query.query_parameters,
        )
        check_request_headers(
            esi_api=self._esi_api,
            operation_id=query.operation_id,
            header_params=query.headers,
        )
        check_request_body_parameters(
            esi_api=self._esi_api,
            operation_id=query.operation_id,
            body_params=query.request_body,
        )


def check_valid_operation_id(
    esi_api: EsiApiProtocol,
    operation_id: str,
) -> None:
    """Check if the given operation ID is valid.

    Args:
        operation_id (str): The operation ID to check.
    """
    try:
        _ = esi_api.indexed_operation(operation_id)
    except ValueError as e:
        raise ValidationError(f"Invalid operation ID: {operation_id}") from e


def check_path_parameters(
    esi_api: EsiApiProtocol,
    operation_id: str,
    path_params: dict[str, str | int | float],
) -> bool:
    """Check if the required path parameters are present for the given operation ID.

    Args:
        op_id (str): The operation ID.
        operation (Literal["get", "put", "post", "delete"]): The HTTP operation type.
        path_params (dict[str, str]): A dictionary of path parameters.

    Returns:
        bool: True if all required path parameters are present, False otherwise.
    """
    # Get a dict of required path parameters from the spec
    operation = esi_api.indexed_operation(operation_id)
    required_params = OA.request_path_parameters(operation)

    # Check no extra path parameters are provided in path_params
    if not all(path_param in required_params for path_param in path_params):
        raise ValidationError(
            f"Unrecognized path parameters given.:{path_params=!r}, {required_params=!r}"
        )

    # Check if all required parameters are present in the provided path_params
    if not all(required_param in path_params for required_param in required_params):
        raise ValidationError(
            f"Missing required path parameters: {path_params=!r}, {required_params=!r}"
        )
    return True


def check_query_parameters(
    esi_api: EsiApiProtocol,
    operation_id: str,
    query_params: dict[str, str | int | float],
) -> bool:
    """Check if the required query parameters are present for the given operation ID.

    Args:
        op_id (str): The operation ID.
        query_params (dict[str, str]): A dictionary of query parameters.

    Returns:
        bool: True if all required query parameters are present, False otherwise.
    """
    # Get the list of required query parameters from the spec
    operation = esi_api.indexed_operation(operation_id)
    possible_params = OA.request_query_parameters(operation)

    # Check no extra query parameters are provided in query_params
    if not all(query_param in possible_params for query_param in query_params):
        raise ValidationError(
            f"Unrecognized query parameters given: {query_params=!r}, {possible_params=!r}"
        )

    # Check if all required parameters are present in the provided query_params
    for key, value in possible_params.items():
        if value.get("required", False):
            if key not in query_params:
                raise ValidationError(
                    f"Missing required query parameters: {query_params=!r}, {possible_params=!r}, "
                )
    return True


def check_request_headers(
    esi_api: EsiApiProtocol,
    operation_id: str,
    header_params: dict[str, str | int | float],
) -> None:
    """Check if the required header parameters are present for the given operation ID.

    Args:
        op_id (str): The operation ID.
        header_params (dict[str, str]): A dictionary of header parameters.

    Returns:
        bool: True if all required header parameters are present, False otherwise.
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
    esi_api: EsiApiProtocol,
    operation_id: str,
    body_params: dict[str, Any],
) -> None:
    """Check if the request body parameters are valid for the given operation ID.

    Args:
        op_id (str): The operation ID.
        body_params (dict): The request body parameters.

    Returns:
        bool: True if the request body parameters are valid, False otherwise.
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
