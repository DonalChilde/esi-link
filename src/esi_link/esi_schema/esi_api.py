"""Code to interact with the Eve Esi openapi spec.

https://swagger.io/specification/
"""

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from whenever import Instant

# from esi_link.esi_schema.schema_pydantic import Operation, Parameter
from esi_link.helpers.resolve_json_ref import resolve_internal_refs

from . import operation_accessors as OA
from .esi_api_protocol import (
    EsiApiProtocol,
    IndexedOperation,
    IndexedOperations,
    SplitParameters,
)
from .schema_store import SchemaStore

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
# TODO output a table of operation_ids,paths, descriptions, and valid inputs.
# TODO store operation lookup as dict. operation_id={path:str,method:str}?
# TODO Refactor to split functions from class, eg def is_paged(api: EsiApiProtocol, operation_id: str) -> bool:


class EsiApi(EsiApiProtocol):
    def __init__(
        self,
        compatibility_date: str,
        schema_path: Path | None = None,
        spec: dict[str, Any] | None = None,
        base_url: str = "https://esi.evetech.net/latest",
    ) -> None:
        """Initialize the EveOpenApi client."""
        if schema_path is None and spec is None:
            raise ValueError("Either schema_path or schema must be provided.")
        self.schema_path = schema_path
        schema_ = spec or self._load_spec()
        validated_schema = self._validate_schema(schema_)
        self.schema: dict[str, Any] = validated_schema
        self.compatibility_date = compatibility_date
        self.base_url = base_url
        self.indexed_operations: IndexedOperations = OA.index_operations(self.schema)

    @classmethod
    def from_schema_store_path(cls, file_path: Path | None) -> "EsiApi":
        """Create an EveOpenApi instance from a schema store file.

        If file_path is None, SchemaStore will download the schema.
        """
        store = SchemaStore(store_path=file_path)
        download_date = Instant.parse_rfc2822(store.download_date)
        compatibility_date = download_date.py_datetime().date().isoformat()
        spec = store.esi_schema
        return cls(compatibility_date=compatibility_date, spec=spec)

    @classmethod
    def from_schema_store(cls, schema_store: SchemaStore) -> "EsiApi":
        """Create an EveOpenApi instance from a SchemaStore."""
        download_date = Instant.parse_rfc2822(schema_store.download_date)
        compatibility_date = download_date.py_datetime().date().isoformat()
        spec = schema_store.esi_schema
        return cls(compatibility_date=compatibility_date, spec=spec)

    def _validate_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        if "openapi" not in schema:
            raise ValueError("Invalid schema: missing 'openapi' field")
        resolved_schema = resolve_internal_refs(parent=schema, child=schema)
        return resolved_schema

    # def _index_by_operation_id(self) -> dict[str, IndexedOperation]:
    #     """Index the operations by their ID."""
    #     by_operation_id: dict[str, IndexedOperation] = {}
    #     for path, methods in self.schema.get("paths", {}).items():
    #         for method, operation in methods.items():
    #             operation_id = operation.get("operationId")
    #             response_codes = list(operation.get("responses", {}).keys())
    #             if len(response_codes) == 1 and response_codes[0] in (
    #                 "200",
    #                 "201",
    #                 "204",
    #             ):
    #                 success_code = response_codes[0]
    #             else:
    #                 logger.warning(
    #                     f"Operation {operation_id} has multiple or no success codes: {response_codes}. Defaulting to empty string."
    #                 )
    #                 success_code = ""
    #             if operation_id:
    #                 by_operation_id[operation_id] = IndexedOperation(
    #                     operation_id=operation_id,
    #                     method=method,
    #                     path=path,
    #                     operation=operation,
    #                     success_code=success_code,
    #                 )
    #     return by_operation_id

    def _load_spec(self) -> dict[str, Any]:
        """Load the OpenAPI specification from the specified file."""
        if self.schema_path is None or not self.schema_path.exists():
            raise ValueError(f"Spec path is invalid: {self.schema_path}")
        with open(self.schema_path, encoding="utf-8") as file:
            return json.load(file)

    # def _check_path_params(
    #     self,
    #     operation_id: str,
    #     path_params: Mapping[str, str | int | float],
    # ) -> bool:
    #     """Check if the required path parameters are present for the given operation ID.

    #     Args:
    #         op_id (str): The operation ID.
    #         operation (Literal["get", "put", "post", "delete"]): The HTTP operation type.
    #         path_params (dict[str, str]): A dictionary of path parameters.

    #     Returns:
    #         bool: True if all required path parameters are present, False otherwise.
    #     """
    #     # Get a dict of required path parameters from the spec
    #     operation = self.indexed_operation(operation_id)
    #     required_params = OA.request_path_parameters(operation)

    #     # Check no extra path parameters are provided in path_params
    #     if not all(path_param in required_params for path_param in path_params):
    #         raise ValueError(
    #             f"Unrecognized path parameters given.:{path_params=}, {required_params=}"
    #         )

    #     # Check if all required parameters are present in the provided path_params
    #     if not all(required_param in path_params for required_param in required_params):
    #         raise ValueError(
    #             f"Missing required path parameters: {path_params=}, {required_params=}"
    #         )
    #     return True

    # def _check_query(
    #     self,
    #     operation_id: str,
    #     query_params: Mapping[str, str | int | float],
    # ) -> bool:
    #     """Check if the required query parameters are present for the given operation ID.

    #     Args:
    #         op_id (str): The operation ID.
    #         query_params (dict[str, str]): A dictionary of query parameters.

    #     Returns:
    #         bool: True if all required query parameters are present, False otherwise.
    #     """
    #     # Get the list of required query parameters from the spec
    #     operation = self.indexed_operation(operation_id)
    #     possible_params = OA.request_query_parameters(operation)

    #     # Check no extra query parameters are provided in query_params
    #     if not all(query_param in possible_params for query_param in query_params):
    #         raise ValueError(
    #             f"Unrecognized query parameters given: {query_params=}, {possible_params=}"
    #         )

    #     # Check if all required parameters are present in the provided query_params
    #     for key, value in possible_params.items():
    #         if value.get("required", False):
    #             if key not in query_params:
    #                 raise ValueError(
    #                     f"Missing required query parameters: {query_params=}, {possible_params=}"
    #                 )
    #     return True

    def split_request_parameters(
        self, operation_id: str, parameters: dict[str, str]
    ) -> SplitParameters:
        """Split the parameters into their respective categories."""
        split_params = SplitParameters()
        operation = self.indexed_operation(operation_id)

        for key, value in parameters.items():
            if key in OA.request_path_parameters(operation):
                split_params.path[key] = value
            elif key in OA.request_query_parameters(operation):
                split_params.query[key] = value
            elif key in OA.request_header_parameters(operation):
                split_params.header[key] = value
            else:
                split_params.unknown[key] = value
        return split_params

    # def validate_operation(
    #     self,
    #     operation_id: str,
    #     path_params: Mapping[str, str | int | float],
    #     query_params: Mapping[str, str | int | float],
    # ) -> bool:
    #     """Validate the operation parameters."""
    #     if operation_id not in self.indexed_operations:
    #         raise ValueError(f"Operation ID not found: {operation_id}")
    #     valid = all(
    #         (
    #             self._check_path_params(
    #                 operation_id=operation_id, path_params=path_params
    #             ),
    #             self._check_query(operation_id=operation_id, query_params=query_params),
    #         ),
    #     )
    #     return valid

    def build_url(
        self,
        operation_id: str,
        path_params: Mapping[str, str | int | float],
        query_params: Mapping[str, str | int | float],
        include_query: bool = False,
    ) -> str:
        """Build a complete URL by combining the base URL, operation ID, path parameters, and query parameters.

        Args:
            operation_id (str): The operation ID (path component).
            path_params (dict[str, str]): A dictionary of path parameters to include in the URL.
            query_params (dict[str, str]): A dictionary of query parameters to include in the URL.
            include_query (bool): Whether to include the query parameters in the URL.

        Returns:
            str: The constructed URL.
        """
        # self.validate_operation(
        #     operation_id=operation_id,
        #     path_params=path_params,
        #     query_params=query_params,
        # )
        # Build the path by replacing placeholders with actual values
        operation = self.indexed_operation(operation_id)
        path_template = operation.path
        path = path_template.format(**path_params)
        resolved_url = f"{self.base_url.strip('/')}/{path.strip('/')}"
        if include_query:
            # Construct the query string from the query parameters
            # Sort keys so URL is stable regardless of dict insertion order
            query_items = sorted(query_params.items(), key=lambda kv: kv[0])
            query_string = "&".join([f"{key}={value}" for key, value in query_items])
            # Combine the path and query string into the final URL
            return f"{resolved_url}?{query_string}" if query_string else resolved_url
        return resolved_url

    def is_paged(self, operation_id: str) -> bool:
        """Check if the operation is paged."""
        operation = self.indexed_operation(operation_id)

        if "X-Pages" in OA.response_200_headers(operation):
            return True
        return False

    def is_cached(self, operation_id: str) -> bool:
        """Check if the operation is cached."""
        operation = self.indexed_operation(operation_id)
        if not operation:
            raise ValueError(f"Operation ID not found: {operation_id}")
        # TODO currently only get methods are cached. Figure out how and when to cache other methods.
        if operation.method.lower() == "get":
            return True
        return False

    def indexed_operation(self, operation_id: str) -> IndexedOperation:
        op_schema = self.indexed_operations.get(operation_id)
        if not op_schema:
            raise ValueError(f"Operation ID not found: {operation_id}")
        return op_schema

    def operation_method(self, operation_id: str) -> str:
        if operation_id not in self.indexed_operations:
            raise ValueError(f"Operation ID not found: {operation_id}")
        operation = self.indexed_operations[operation_id]
        return operation.method

    def operation_path(self, operation_id: str) -> str:
        if operation_id not in self.indexed_operations:
            raise ValueError(f"Operation ID not found: {operation_id}")
        operation = self.indexed_operations[operation_id]
        return operation.path

    # def request_parameters(self, operation_id: str) -> Sequence[Parameter]:
    #     """Collect the request parameters for the given operation ID from the schema.

    #     Args:
    #         operation_id (str): The operation ID.

    #     Returns:
    #         dict[str, dict[str, Any]]: A dictionary of request parameters.
    #     """
    #     operation_schema = self.operation_schema(operation_id)
    #     request_parameters = operation_schema.operation.parameters
    #     return request_parameters

    # def response_content(self, operation_id: str) -> dict[str, dict[str, Any]]:
    #     """Collect the status 200 response content for the given operation ID from the schema.

    #     Args:
    #         operation_id (str): The operation ID.

    #     Returns:
    #         dict[str, dict[str, Any]]: A dictionary of response parameters.
    #     """
    #     operation_schema = self.operation_schema(operation_id)
    #     response_content = operation_schema.operation.responses.get("200", {}).get(
    #         "content", {}
    #     )
    #     return response_content

    # def response_headers(self, operation_id: str) -> dict[str, dict[str, Any]]:
    #     """Collect the status 200 response headers for the given operation ID from the schema.

    #     Args:
    #         operation_id (str): The operation ID.

    #     Returns:
    #         dict[str, dict[str, Any]]: A dictionary of response headers.
    #     """
    #     operation_schema = self.operation_schema(operation_id)
    #     response_headers = operation_schema.operation.responses.get("200", {}).get(
    #         "headers", {}
    #     )
    #     return response_headers
