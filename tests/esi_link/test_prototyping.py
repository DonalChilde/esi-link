from dataclasses import dataclass, field
from pathlib import Path
from pprint import pprint
from typing import Any

from pydantic import BaseModel

from esi_link.esi_schema.schema_store import SchemaStore


class Example(BaseModel):
    file_path: Path


@dataclass
class OperationData:
    operation_keys: set[str] = field(default_factory=set[str])

    def __str__(self) -> str:
        return f"OperationData(operation_keys={self.operation_keys})"


def test_response_content_schema_types(schema_store: SchemaStore):
    methods: dict[str, Any] = {}
    for path, operations in schema_store.esi_schema.get("paths", {}).items():
        for method, operation in operations.items():
            if method not in methods:
                methods[method] = {"operation_data": OperationData()}
            for key in operation.keys():
                methods[method]["operation_data"].operation_keys.add(key)

    pprint(methods, indent=2)
    # assert False
