"""Accessor functions for ESI schema operations."""

import logging
from dataclasses import dataclass
from typing import Any, Literal

from esi_link.esi_schema.esi_api_protocol import IndexedOperation, IndexedOperations

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass
class TagOperationDetails:
    operation_id: str
    description: str
    requires_auth: bool


TagMapOperationDetails = dict[str, list[TagOperationDetails]]
"""Dict of tag names to list of operation details."""


def is_cached(operation_schema: IndexedOperation) -> bool:
    """Check if an operation is cached."""
    # This might be correct, needs some testing.
    # previously used get method to test for cache.
    return "x-cache-age" in operation_schema.operation


def is_paged(operation_schema: IndexedOperation) -> bool:
    """Check if an operation is paged."""
    return any(
        param.get("name") == "page"
        for param in operation_schema.operation.get("parameters", [])
        if param.get("in") == "query"
    )


def is_auth_required(operation_schema: IndexedOperation) -> bool:
    """Check if an operation requires authentication."""
    return bool(operation_schema.operation.get("security"))


def oauth2_scopes(operation_schema: IndexedOperation) -> list[str]:
    """Get the authentication scopes required for an operation."""
    security: list[dict[str, Any]] = operation_schema.operation.get("security", [])
    scopes: list[str] = []
    if security:
        for sec in security:
            if "OAuth2" in sec:
                scopes.extend(sec["OAuth2"])
    return scopes


def x_cache_age(operation_schema: IndexedOperation) -> int | None:
    """Get the x-cache-age for an operation, if any."""
    return operation_schema.operation.get("x-cache-age")


def x_compatibility_date(operation_schema: IndexedOperation) -> str | None:
    """Get the x-compatibility-date for an operation, if any."""
    return operation_schema.operation.get("x-compatibility-date")


def request_parameters(operation_schema: IndexedOperation) -> dict[str, dict[str, Any]]:
    """Get the request parameters for an operation."""
    return {
        param["name"]: param
        for param in operation_schema.operation.get("parameters", [])
    }


def tags(operation_schema: IndexedOperation) -> list[str]:
    """Get the tags for an operation."""
    return operation_schema.operation.get("tags", [])


def description(operation_schema: IndexedOperation) -> str:
    """Get the description for an operation."""
    op_description: str = operation_schema.operation.get("description", "")
    return op_description.strip().replace("\n", " ")


def request_header_parameters(
    operation_schema: IndexedOperation,
) -> dict[str, dict[str, Any]]:
    """Get the request headers for an operation."""
    return {
        param["name"]: param
        for param in operation_schema.operation.get("parameters", [])
        if param.get("in") == "header"
    }


def request_query_parameters(
    operation_schema: IndexedOperation,
) -> dict[str, dict[str, Any]]:
    """Get the request query parameters for an operation."""
    return {
        param["name"]: param
        for param in operation_schema.operation.get("parameters", [])
        if param.get("in") == "query"
    }


def request_path_parameters(
    operation_schema: IndexedOperation,
) -> dict[str, dict[str, Any]]:
    """Get the request path parameters for an operation."""
    return {
        param["name"]: param
        for param in operation_schema.operation.get("parameters", [])
        if param.get("in") == "path"
    }


def request_body(operation_schema: IndexedOperation) -> dict[str, Any] | None:
    """Get the request body schema for an operation, if any."""
    return operation_schema.operation.get("requestBody")


def response_200_content(operation_schema: IndexedOperation) -> dict[str, Any]:
    """Get the response content for a 200 response in an operation."""
    return (
        operation_schema.operation.get("responses", {})
        .get("200", {})
        .get("content", {})
    )


def response_200_schema(operation_schema: IndexedOperation) -> dict[str, Any]:
    """Get the response schema for a 200 response in an operation, if any."""
    return (
        operation_schema.operation.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )


def response_200_headers(operation_schema: IndexedOperation) -> dict[str, Any]:
    """Get the response headers for a 200 response in an operation."""
    return (
        operation_schema.operation.get("responses", {})
        .get("200", {})
        .get("headers", {})
    )


def response_204_content(operation_schema: IndexedOperation) -> dict[str, Any]:
    """Get the response content for a 204 response in an operation."""
    return (
        operation_schema.operation.get("responses", {})
        .get("204", {})
        .get("content", {})
    )


def response_204_schema(operation_schema: IndexedOperation) -> dict[str, Any] | None:
    """Get the response schema for a 204 response in an operation, if any."""
    return (
        operation_schema.operation.get("responses", {})
        .get("204", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )


def response_204_headers(operation_schema: IndexedOperation) -> dict[str, Any]:
    """Get the response headers for a 204 response in an operation."""
    return (
        operation_schema.operation.get("responses", {})
        .get("204", {})
        .get("headers", {})
    )


def response_201_content(operation_schema: IndexedOperation) -> dict[str, Any]:
    """Get the response content for a 201 response in an operation."""
    return (
        operation_schema.operation.get("responses", {})
        .get("201", {})
        .get("content", {})
    )


def response_201_schema(operation_schema: IndexedOperation) -> dict[str, Any] | None:
    """Get the response schema for a 201 response in an operation, if any."""
    return (
        operation_schema.operation.get("responses", {})
        .get("201", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )


def response_201_headers(operation_schema: IndexedOperation) -> dict[str, Any]:
    """Get the response headers for a 201 response in an operation."""
    return (
        operation_schema.operation.get("responses", {})
        .get("201", {})
        .get("headers", {})
    )


def operations_by_tag(
    indexed_operations: dict[str, IndexedOperation],
) -> TagMapOperationDetails:
    """Group operation_ids by their tags.

    Tags are sorted alphabetically, and operations within each tag are also sorted alphabetically.
    """
    tag_map: TagMapOperationDetails = {}
    for indexed_operation in indexed_operations.values():
        op_tags = tags(indexed_operation)
        for tag in op_tags:
            details = TagOperationDetails(
                operation_id=indexed_operation.operation_id,
                description=description(indexed_operation),
                requires_auth=is_auth_required(indexed_operation),
            )
            tag_map.setdefault(tag, []).append(details)
    sorted_tag_map: TagMapOperationDetails = dict(sorted(tag_map.items()))
    # sort operations within each tag by operation_id
    for tag, indexed_operations in sorted_tag_map.items():  # type: ignore
        sorted_tag_map[tag] = sorted(indexed_operations, key=lambda op: op.operation_id)  # type: ignore
    return sorted_tag_map


def operation_by_path_method(
    path: str, method: Literal["get", "post", "put", "delete"], schema: dict[str, Any]
) -> IndexedOperation:
    """Get the OperationSchema for a given path and method."""
    path_data = schema.get("paths", {})
    if path not in path_data:
        raise KeyError(f"Path '{path}' not found in schema.")
    method_data = path_data.get(method, {})
    if not method_data:
        raise KeyError(
            f"Method '{method}' not found for path '{path}' in schema. Available methods are {path_data.keys()}"
        )
    return IndexedOperation(
        operation_id=method_data["operationId"],
        method=method,
        path=path,
        operation=method_data,
    )


def index_operations(schema: dict[str, dict[str, Any]]) -> IndexedOperations:
    """Index the operations by their ID."""
    by_operation_id: IndexedOperations = {}
    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            operation_id = operation.get("operationId")
            response_codes = list(operation.get("responses", {}).keys())
            response_codes.remove("default") if "default" in response_codes else None
            if len(response_codes) == 1 and response_codes[0] in (
                "200",
                "201",
                "204",
            ):
                success_code = response_codes[0]
            else:
                logger.warning(
                    f"Operation {operation_id} has multiple or no success codes: {response_codes}. Defaulting to empty string."
                )
                # TODO decide how to handle multiple success codes, maye use space delimited string?
                success_code = ""
            if operation_id:
                by_operation_id[operation_id] = IndexedOperation(
                    operation_id=operation_id,
                    method=method,
                    path=path,
                    operation=operation,
                    success_code=success_code,
                )
    return by_operation_id
