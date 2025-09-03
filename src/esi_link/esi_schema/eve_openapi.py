"""Code to interact with the Eve Esi openapi spec.

https://swagger.io/specification/
"""

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from esi_link.esi_schema.schema_pydantic import Operation, OperationSchema, Parameter
from esi_link.helpers.resolve_json_ref import resolve_internal_refs

from .eve_openapi_protocol import (
    EveOpenApiProtocol,
    SplitParameters,
)
from .schema_store import SchemaStore

# FIXME decide on validation signalling. right now the functions return a bool, and throw an exception.
# TODO output a table of operation_ids,paths, descriptions, and valid inputs.


class EveOpenApi(EveOpenApiProtocol):
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
        self.by_operation_id: dict[str, OperationSchema] = self._index_by_operation_id()

    @classmethod
    def from_schema_store_path(cls, file_path: Path | None) -> "EveOpenApi":
        """Create an EveOpenApi instance from a schema store file.

        If file_path is None, SchemaStore will download the schema.
        """
        store = SchemaStore(store_path=file_path)
        download_date = datetime.fromisoformat(store.download_date)
        compatibility_date = download_date.date().isoformat()
        spec = store.esi_schema
        return cls(compatibility_date=compatibility_date, spec=spec)

    @classmethod
    def from_schema_store(cls, schema_store: SchemaStore) -> "EveOpenApi":
        """Create an EveOpenApi instance from a SchemaStore."""
        download_date = datetime.fromisoformat(schema_store.download_date)
        compatibility_date = download_date.date().isoformat()
        spec = schema_store.esi_schema
        return cls(compatibility_date=compatibility_date, spec=spec)

    def _validate_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        if "openapi" not in schema:
            raise ValueError("Invalid schema: missing 'openapi' field")
        resolved_schema = resolve_internal_refs(parent=schema, child=schema)
        return resolved_schema

    # def _resolve_ref(self, reference: str) -> dict[str, Any]:
    #     """Resolve a JSON reference (RFC 6901) to its definition in the spec."""
    #     if reference.startswith("#/"):
    #         # Resolve internal reference
    #         parts = reference[2:].split("/")
    #         return self._resolve_internal_ref(parts)
    #     return {}

    # def _resolve_internal_ref(self, parts: list[str]) -> dict[str, Any]:
    #     """Resolve an internal JSON reference given as a list of path parts."""
    #     obj = self.spec
    #     for part in parts:
    #         if isinstance(obj, dict):
    #             obj = obj.get(part)
    #         else:
    #             return {}
    #     return obj if isinstance(obj, dict) else {}

    # def _common_response_headers(self) -> dict[str, dict[str, Any]]:
    #     response_headers = {}
    #     for header in self.spec.get("components", {}).get("headers", {}).values():
    #         response_headers[header["name"]] = header
    #     return response_headers

    # def _common_request_headers(self) -> dict[str, dict[str, Any]]:
    #     request_headers = {}
    #     for header in self.spec.get("components", {}).get("headers", {}).values():
    #         if header.get("in") == "header":
    #             request_headers[header["name"]] = header
    #     return request_headers

    # def _operation_specific_response_parameters(
    #     self, operation_id: str
    # ) -> dict[str, dict[str, Any]]:
    #     """Get the response headers specific to the given operation ID."""
    #     operation = self.by_op_id.get(operation_id, {})
    #     response_headers: dict[str, dict[str, Any]] = {}
    #     for key, value in (
    #         operation.get("operation", {})
    #         .get("responses", {})
    #         .get("200", {})
    #         .get("headers", {})
    #         .items()
    #     ):
    #         if "$ref" in value:
    #             response_headers[key] = self._resolve_ref(value["$ref"])
    #         else:
    #             response_headers[key] = value
    #     return response_headers

    # def _operation_specific_request_parameters(
    #     self, operation_id: str
    # ) -> dict[str, dict[str, Any]]:
    #     """Get the request parameters specific to the given operation ID."""
    #     operation = self.by_op_id.get(operation_id, {})
    #     request_parameters: dict[str, dict[str, Any]] = {}
    #     for value in operation.get("operation", {}).get("parameters", []):
    #         if "$ref" in value:
    #             value = self._resolve_ref(value["$ref"])
    #             request_parameters[value["name"]] = value
    #         else:
    #             request_parameters[value["name"]] = value
    #     return request_parameters

    def _index_by_operation_id(self) -> dict[str, OperationSchema]:
        """Index the operations by their ID."""
        by_operation_id: dict[str, OperationSchema] = {}
        for path, methods in self.schema.get("paths", {}).items():
            for method, operation in methods.items():
                operation_id = operation.get("operationId")
                if operation_id:
                    by_operation_id[operation_id] = OperationSchema(
                        operation_id=operation_id,
                        method=method,
                        path=path,
                        operation=operation,
                    )
        return by_operation_id

    def _load_spec(self) -> dict[str, Any]:
        """Load the OpenAPI specification from the specified file."""
        if self.schema_path is None or not self.schema_path.exists():
            raise ValueError(f"Spec path is invalid: {self.schema_path}")
        with open(self.schema_path, encoding="utf-8") as file:
            return json.load(file)

    # def _collect_path_params(self, op_id: str) -> dict[str, dict[str, Any]]:
    #     """Collect the path parameters for the given operation ID from the schema.

    #     Args:
    #         op_id (str): The operation ID.

    #     Returns:
    #         dict[str, dict[str, Any]]: A dictionary of path parameter definitions keyed by
    #         parameter name.

    #     Example:
    #         For ``op_id='GetMarketsRegionIdHistory'`` (path ``/markets/{region_id}/history``)
    #         this function returns a mapping like:

    #             {
    #                 "region_id": {
    #                     "in": "path",
    #                     "name": "region_id",
    #                     "required": True,
    #                     "schema": {
    #                         "description": "Return statistics in this region",
    #                         "format": "int64",
    #                         "type": "integer"
    #                     }
    #                 }
    #             }
    #     """
    #     # Get the path parameters from the spec
    #     # path parameters must have unique names, so we use a dict to enforce this.
    #     op_parameters = self._operation_specific_request_parameters(operation_id=op_id)
    #     path_parameters = {}
    #     for key, param in op_parameters.items():
    #         if param.get("in") == "path":
    #             path_parameters[key] = param
    #     return path_parameters

    def _check_path_params(
        self,
        operation_id: str,
        path_params: Mapping[str, str | int | float],
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
        required_params = {
            x["name"]: x
            for x in self.request_parameters(operation_id)
            if x.get("in", "") == "path"
        }

        # Check no extra path parameters are provided in path_params
        if not all(path_param in required_params for path_param in path_params):
            raise ValueError(
                f"Unrecognized path parameters given.:{path_params=}, {required_params=}"
            )

        # Check if all required parameters are present in the provided path_params
        if not all(required_param in path_params for required_param in required_params):
            raise ValueError(
                f"Missing required path parameters: {path_params=}, {required_params=}"
            )
        return True

    # def _collect_path(self, op_id: str) -> str:
    #     """Get the path for the given operation ID.

    #     Args:
    #         op_id (str): The operation ID.

    #     Returns:
    #         str: The path for the operation.
    #     """
    #     path = self.by_op_id.get(op_id, {}).get("path")
    #     if not path:
    #         raise ValueError(f"Path not found for operation ID: {op_id}")
    #     return path

    # def _collect_query_params(self, op_id: str) -> dict[str, dict[str, Any]]:
    #     """Collect the query parameters for the given operation ID from the schema.

    #     Args:
    #         op_id (str): The operation ID.

    #     Returns:
    #         dict[str, dict[str, Any]]: A dictionary of query parameter definitions
    #         keyed by parameter name.

    #     Example:
    #         For ``op_id='GetMarketsRegionIdHistory'`` (path ``/markets/{region_id}/history``)
    #         this function returns a mapping like:

    #             {
    #                 "type_id": {
    #                     "in": "query",
    #                     "name": "type_id",
    #                     "required": True,
    #                     "schema": {
    #                         "description": "Return statistics for this type",
    #                         "format": "int64",
    #                         "type": "integer"
    #                     }
    #                 }
    #             }
    #     """
    #     # Get the query parameters from the spec
    #     # Query strings do not have to have unique names, but Eve esi uses unique names
    #     # for query parameters, and they are all defined in the operation path.
    #     operation_parameters = self._operation_specific_request_parameters(
    #         operation_id=op_id
    #     )
    #     query_params = {}
    #     for key, param in operation_parameters.items():
    #         if param.get("in") == "query":
    #             query_params[key] = param
    #     return query_params

    def _check_query(
        self,
        operation_id: str,
        query_params: Mapping[str, str | int | float],
    ) -> bool:
        """Check if the required query parameters are present for the given operation ID.

        Args:
            op_id (str): The operation ID.
            query_params (dict[str, str]): A dictionary of query parameters.

        Returns:
            bool: True if all required query parameters are present, False otherwise.
        """
        # Get the list of required query parameters from the spec
        possible_params = {
            x["name"]: x
            for x in self.request_parameters(operation_id)
            if x.get("in", "") == "query"
        }

        # Check no extra query parameters are provided in query_params
        if not all(query_param in possible_params for query_param in query_params):
            raise ValueError(
                f"Unrecognized query parameters given: {query_params=}, {possible_params=}"
            )

        # Check if all required parameters are present in the provided query_params
        for key, value in possible_params.items():
            if value.get("required", False):
                if key not in query_params:
                    raise ValueError(
                        f"Missing required query parameters: {query_params=}, {possible_params=}"
                    )
        return True

    def split_parameters(
        self, operation_id: str, parameters: Mapping[str, str | int | float]
    ) -> SplitParameters:
        raise NotImplementedError("Subclasses must implement split_parameters")

    def validate_operation(
        self,
        operation_id: str,
        path_params: Mapping[str, str | int | float],
        query_params: Mapping[str, str | int | float],
    ) -> bool:
        """Validate the operation parameters."""
        if operation_id not in self.by_operation_id:
            raise ValueError(f"Operation ID not found: {operation_id}")
        valid = all(
            (
                self._check_path_params(
                    operation_id=operation_id, path_params=path_params
                ),
                self._check_query(operation_id=operation_id, query_params=query_params),
            ),
        )
        return valid

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
        self.validate_operation(
            operation_id=operation_id,
            path_params=path_params,
            query_params=query_params,
        )
        # Build the path by replacing placeholders with actual values
        operation = self.operation_schema(operation_id)
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
        if "X-Pages" in self.response_headers(operation_id):
            return True
        return False

    def is_cached(self, operation_id: str) -> bool:
        """Check if the operation is cached."""
        operation = self.operation_schema(operation_id)
        if not operation:
            raise ValueError(f"Operation ID not found: {operation_id}")
        # TODO currently only get methods are cached. Figure out how and when to cache other methods.
        if operation.method.lower() == "get":
            return True
        return False

    # def _collect_request_headers(self, op_id: str) -> dict[str, dict[str, Any]]:
    #     """Collect the headers for the given operation ID from the schema.

    #     Args:
    #         op_id (str): The operation ID.

    #     Returns:
    #         dict[str, dict[str, Any]]: A dictionary of headers.
    #     """
    #     request_parameters = self._operation_specific_request_parameters(op_id)
    #     request_headers = {}
    #     for key, param in request_parameters.items():
    #         if param.get("in") == "header":
    #             request_headers[key] = param
    #     return request_headers

    # def _collect_response_headers(self, op_id: str) -> dict[str, dict[str, Any]]:
    #     """Collect the possible response headers for the given operation ID from the schema.

    #     Includes headers in common, and those specific to the operation.

    #     Args:
    #         op_id (str): The operation ID.

    #     Returns:
    #         dict[str, dict[str, Any]]: A dictionary of response headers.
    #     """
    #     response_parameters = self._operation_specific_response_parameters(op_id)
    #     response_headers = {}
    #     for key, param in response_parameters.items():
    #         if param.get("in") == "header":
    #             response_headers[key] = param
    #     return response_headers

    def operation_schema(self, operation_id: str) -> OperationSchema:
        op_schema = self.by_operation_id.get(operation_id)
        if not op_schema:
            raise ValueError(f"Operation ID not found: {operation_id}")
        return op_schema

    def operation_method(self, operation_id: str) -> str:
        if operation_id not in self.by_operation_id:
            raise ValueError(f"Operation ID not found: {operation_id}")
        operation = self.by_operation_id[operation_id]
        return operation.method

    def operation_path(self, operation_id: str) -> str:
        if operation_id not in self.by_operation_id:
            raise ValueError(f"Operation ID not found: {operation_id}")
        operation = self.by_operation_id[operation_id]
        return operation.path

    def request_parameters(self, operation_id: str) -> Sequence[Parameter]:
        """Collect the request parameters for the given operation ID from the schema.

        Args:
            operation_id (str): The operation ID.

        Returns:
            dict[str, dict[str, Any]]: A dictionary of request parameters.
        """
        operation_schema = self.operation_schema(operation_id)
        request_parameters = operation_schema.operation.parameters
        return request_parameters

    def response_content(self, operation_id: str) -> dict[str, dict[str, Any]]:
        """Collect the status 200 response content for the given operation ID from the schema.

        Args:
            operation_id (str): The operation ID.

        Returns:
            dict[str, dict[str, Any]]: A dictionary of response parameters.
        """
        operation_schema = self.operation_schema(operation_id)
        response_content = operation_schema.operation.responses.get("200", {}).get(
            "content", {}
        )
        return response_content

    def response_headers(self, operation_id: str) -> dict[str, dict[str, Any]]:
        """Collect the status 200 response headers for the given operation ID from the schema.

        Args:
            operation_id (str): The operation ID.

        Returns:
            dict[str, dict[str, Any]]: A dictionary of response headers.
        """
        operation_schema = self.operation_schema(operation_id)
        response_headers = operation_schema.operation.responses.get("200", {}).get(
            "headers", {}
        )
        return response_headers
