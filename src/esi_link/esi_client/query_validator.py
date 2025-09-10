from typing import Protocol

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

    def __init__(self, eve_api: EsiApiProtocol) -> None:
        self._eve_api = eve_api

    def validate(self, query: EsiQuery) -> None:
        """Validate the given ESI query.

        Args:
            query (EsiQuery): The query to validate.

        Raises:
            ValidationError: If the query is invalid.
        """
        # Add more validation rules as needed


# def _check_path_params(
#         self,
#         operation_id: str,
#         path_params: Mapping[str, str | int | float],
#     ) -> bool:
#         """Check if the required path parameters are present for the given operation ID.

#         Args:
#             op_id (str): The operation ID.
#             operation (Literal["get", "put", "post", "delete"]): The HTTP operation type.
#             path_params (dict[str, str]): A dictionary of path parameters.

#         Returns:
#             bool: True if all required path parameters are present, False otherwise.
#         """
#         # Get a dict of required path parameters from the spec
#         operation = self.indexed_operation(operation_id)
#         required_params = OA.request_path_parameters(operation)

#         # Check no extra path parameters are provided in path_params
#         if not all(path_param in required_params for path_param in path_params):
#             raise ValueError(
#                 f"Unrecognized path parameters given.:{path_params=}, {required_params=}"
#             )

#         # Check if all required parameters are present in the provided path_params
#         if not all(required_param in path_params for required_param in required_params):
#             raise ValueError(
#                 f"Missing required path parameters: {path_params=}, {required_params=}"
#             )
#         return True

#     def _check_query(
#         self,
#         operation_id: str,
#         query_params: Mapping[str, str | int | float],
#     ) -> bool:
#         """Check if the required query parameters are present for the given operation ID.

#         Args:
#             op_id (str): The operation ID.
#             query_params (dict[str, str]): A dictionary of query parameters.

#         Returns:
#             bool: True if all required query parameters are present, False otherwise.
#         """
#         # Get the list of required query parameters from the spec
#         operation = self.indexed_operation(operation_id)
#         possible_params = OA.request_query_parameters(operation)

#         # Check no extra query parameters are provided in query_params
#         if not all(query_param in possible_params for query_param in query_params):
#             raise ValueError(
#                 f"Unrecognized query parameters given: {query_params=}, {possible_params=}"
#             )

#         # Check if all required parameters are present in the provided query_params
#         for key, value in possible_params.items():
#             if value.get("required", False):
#                 if key not in query_params:
#                     raise ValueError(
#                         f"Missing required query parameters: {query_params=}, {possible_params=}"
#                     )
#         return True
