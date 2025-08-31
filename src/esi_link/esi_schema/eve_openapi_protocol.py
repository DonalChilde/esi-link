"""This module provides entry points for the Eve Online ESI Api.

The openapi 3.1 specification for the ESI can be found at:
https://esi.evetech.net/meta/openapi.json
"""

from collections.abc import Mapping
from typing import Protocol, TypedDict


class SplitParameters(TypedDict):
    path: Mapping[str, str | int | float]
    query: Mapping[str, str | int | float]
    header: Mapping[str, str | int | float]


class EveOpenApiProtocol(Protocol):
    base_url: str = "https://esi.evetech.net/latest"
    compatibility_date: str
    """The compatibility date for the API in YYYY-MM-DD format."""

    def get_url(
        self,
        op_id: str,
        path_params: Mapping[str, str | int | float],
        query_params: Mapping[str, str | int | float],
        include_query: bool = False,
    ) -> str:
        """Build the URL for the given operation ID."""
        ...

    def get_method(self, op_id: str) -> str:
        """Get the HTTP method for the given operation ID."""
        ...

    def validate_operation(
        self,
        op_id: str,
        path_params: Mapping[str, str | int | float],
        query_params: Mapping[str, str | int | float],
    ) -> bool:
        """Validate the operation parameters.

        raise an exception if validation fails.
        """
        ...

    def split_parameters(
        self,
        op_id: str,
        parameters: Mapping[str, str | int | float],
    ) -> SplitParameters:
        """Split the parameters into their respective categories."""
        ...

    def is_paged(self, op_id: str) -> bool:
        """Check if the operation is paged."""
        ...

    def is_cached(self, op_id: str) -> bool:
        """Check if the operation is cached."""
        ...
