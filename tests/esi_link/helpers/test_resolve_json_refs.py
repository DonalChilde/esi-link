import json
from copy import deepcopy
from pathlib import Path

from esi_link.esi_schema.schema_store import SchemaStore
from esi_link.helpers.resolve_json_ref import resolve_internal_refs


def test_resolve_internal_refs_whole(schema_store: SchemaStore, test_output_dir: Path):
    copied_schema = deepcopy(schema_store.esi_schema)
    assert copied_schema == schema_store.esi_schema, (
        "before resolve, original should be unchanged"
    )
    resolved_json = resolve_internal_refs(copied_schema, copied_schema)
    assert copied_schema == schema_store.esi_schema, (
        "after resolve, original should be unchanged"
    )
    resolved_file = test_output_dir / "resolved.json"
    with open(resolved_file, "w") as f:
        json.dump(resolved_json, f, indent=2)
    schema_file = test_output_dir / "schema-post-resolve.json"
    with open(schema_file, "w") as fp:
        json.dump(schema_store.esi_schema, fp, indent=2)

    assert resolved_file.exists()
    assert schema_file.exists()

    parent = {
        "components": {
            "schemas": {
                "A": {"type": "object"},
                "B": {"$ref": "#/components/schemas/A"},
            }
        }
    }
    child = parent["components"]["schemas"]["B"]
    resolved = resolve_internal_refs(parent, child)
    assert resolved == {"type": "object"}
