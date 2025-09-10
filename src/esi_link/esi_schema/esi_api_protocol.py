"""This module provides entry points for the Eve Online ESI Api.

The openapi 3.1 specification for the ESI can be found at:
https://esi.evetech.net/meta/openapi.json
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(slots=True)
class SplitParameters:
    path: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    query: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    header: dict[str, str] = field(default_factory=dict[str, str])
    unknown: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )


@dataclass(slots=True)
class IndexedOperation:
    operation_id: str
    method: str
    path: str
    operation: dict[str, Any] = field(default_factory=dict[str, Any])
    success_code: Literal["200", "201", "204", ""] = "200"


IndexedOperations = Mapping[str, IndexedOperation]


class EsiApiProtocol(Protocol):
    base_url: str = "https://esi.evetech.net/latest"
    compatibility_date: str
    """The compatibility date for the API in YYYY-MM-DD format."""

    def build_url(
        self,
        operation_id: str,
        path_params: Mapping[str, str | int | float],
        query_params: Mapping[str, str | int | float],
        include_query: bool = False,
    ) -> str:
        """Build the URL for the given operation ID."""
        ...

    def operation_method(self, operation_id: str) -> str:
        """Get the HTTP method for the given operation ID."""
        ...

    def operation_path(self, operation_id: str) -> str:
        """Get the path for the given operation ID."""
        ...

    def indexed_operation(self, operation_id: str) -> IndexedOperation:
        """Get the indexed operation for the given operation ID."""
        ...

    def validate_operation(
        self,
        operation_id: str,
        path_params: dict[str, str | int | float],
        query_params: dict[str, str | int | float],
    ) -> bool:
        """Validate the operation parameters.

        raise an exception if validation fails.
        """
        ...

    def split_request_parameters(
        self,
        operation_id: str,
        parameters: dict[str, str],
    ) -> SplitParameters:
        """Split the parameters into their respective categories."""
        ...

    def is_paged(self, operation_id: str) -> bool:
        """Check if the operation is paged."""
        ...

    def is_cached(self, operation_id: str) -> bool:
        """Check if the operation is cached."""
        ...

    # def operation_parameter_schema(
    #     self, op_id: str, location: Literal["query", "path", "header", "cookie"]
    # ) -> list[ST.Parameter]:
    #     """Get the parameter schema for the given operation ID."""
    #     ...
