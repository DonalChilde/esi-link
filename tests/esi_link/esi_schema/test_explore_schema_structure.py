from dataclasses import dataclass, field
from pprint import pprint
from typing import Any

import pytest

from esi_link.esi_schema.eve_openapi import EveOpenApi
from esi_link.esi_schema.schema_pydantic import Content
from esi_link.esi_schema.schema_store import SchemaStore


@dataclass
class OperationData:
    operation_keys: set[str] = field(default_factory=set[str])

    def __str__(self) -> str:
        return f"OperationData(operation_keys={self.operation_keys})"


# @pytest.mark.skip(reason="Prototyping")
def test_response_content_schema_types(schema_store: SchemaStore):
    methods: dict[str, Any] = {}
    for path, operations in schema_store.esi_schema.get("paths", {}).items():
        for method, operation in operations.items():
            if method not in methods:
                methods[method] = {"operation_data": OperationData()}
            for key in operation.keys():
                methods[method]["operation_data"].operation_keys.add(key)

    pprint(methods, indent=2)
    assert False


def test_eve_openapi_schema_structure(schema_store: SchemaStore):
    # Test the structure of the Eve OpenAPI schema
    eve_openapi = EveOpenApi.from_schema_store(schema_store)
    operation = eve_openapi.by_operation_id.get("GetMarketsRegionIdHistory")
    assert operation is not None
    assert operation.operation_id == "GetMarketsRegionIdHistory"
    assert operation.method == "get"
    assert operation.path == "/markets/{region_id}/history"
    for param in operation.operation.parameters:
        if param.in_ == "path":
            assert param.name == "region_id"
    assert operation.operation.request_body is None
    assert operation.operation.responses.a_200 is not None
    assert isinstance(operation.operation.responses.a_200.content, Content)
