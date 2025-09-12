from dataclasses import dataclass, field
from pprint import pprint
from typing import Any

import pytest
from rich.pretty import pprint as rpprint

from esi_link.esi_schema.esi_api import EsiApi
from esi_link.esi_schema.schema_pydantic import Content
from esi_link.esi_schema.schema_store import SchemaStore


@dataclass
class OperationData:
    operation_keys: set[str] = field(default_factory=set[str])
    paged_operations: set[str] = field(default_factory=set[str])
    response_types: set[str] = field(default_factory=set[str])
    paged_response_types: set[str] = field(default_factory=set[str])

    def __str__(self) -> str:
        return f"OperationData(operation_keys={self.operation_keys})"


@pytest.mark.skip(reason="Prototyping")
def test_response_content_schema_types(schema_store: SchemaStore):
    methods: dict[str, Any] = {}
    for path, operations in schema_store.esi_schema.get("paths", {}).items():
        for method, operation in operations.items():
            if method not in methods:
                methods[method] = {"operation_data": OperationData()}
            for key in operation.keys():
                methods[method]["operation_data"].operation_keys.add(key)
            is_paged = bool(
                operation.get("responses", {})
                .get("200", {})
                .get("headers", {})
                .get("X-Pages")
            )
            response_content = (
                operation.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            type_of_response = response_content.get("type", "unknown")
            if response_content.get("items"):
                type_of_response = f"{type_of_response} - items - {response_content['items'].get('type', 'unknown')}"
            else:
                type_of_response = f"{type_of_response} - no items"
                # type_of_items = response_content.get("items", {}).get("type")
            methods[method]["operation_data"].response_types.add(type_of_response)
            if is_paged:
                methods[method]["operation_data"].paged_response_types.add(
                    type_of_response
                )
                methods[method]["operation_data"].paged_operations.add(
                    operation["operationId"]
                )

    rpprint(methods)
    # assert False
