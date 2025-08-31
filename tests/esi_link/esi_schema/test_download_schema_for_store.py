import json
from pathlib import Path

import pytest

from esi_link.esi_schema.schema_store import SchemaStore


@pytest.mark.slow
def test_schema_store_real_download(test_output_dir: Path):
    """Test that SchemaStore downloads the real ESI schema from the default URL."""

    store_path = test_output_dir / "schema-download" / "schema_store.json"
    # Use the default URL from SchemaStore
    assert not store_path.is_file()
    store = SchemaStore.from_download(store_path=store_path)
    # Check that the schema file was written and contains expected keys
    assert store_path.is_file()
    saved = json.loads(store_path.read_text())
    assert "openapi" in saved
    assert store.esi_schema is not None
    assert "openapi" in store.esi_schema


def test_schema_store_fixture(schema_store: SchemaStore):
    """Test the schema_store fixture."""
    assert schema_store.esi_schema is not None
    assert "openapi" in schema_store.esi_schema
