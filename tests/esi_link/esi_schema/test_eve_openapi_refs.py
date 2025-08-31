"""Tests for EveOpenApi reference resolution helpers.

Covers:
- _resolve_ref for internal and non-internal refs
- _resolve_internal_ref for valid paths and non-dict leaf behavior
"""

# pyright: basic
from typing import Any

from esi_link.esi_schema.eve_openapi import EveOpenApi


def test_resolve_ref_components_headers_etag(esi_schema: dict[str, Any]):
    """Internal $ref to a common header should resolve to a dict with schema."""
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    ref = "#/components/headers/ETag"
    resolved = client._resolve_ref(ref)

    assert isinstance(resolved, dict)
    # Basic sanity checks on known header shape
    assert resolved["schema"]["type"] == "string"
    assert "ETag" in resolved.get("description", "")


def test_resolve_ref_components_schemas_alliance_id(esi_schema: dict[str, Any]):
    """Internal $ref to a schema resolves to the expected integer model."""
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    ref = "#/components/schemas/AllianceID"
    resolved = client._resolve_ref(ref)

    assert isinstance(resolved, dict)
    assert resolved["type"] == "integer"
    assert resolved["format"] == "int64"


def test_resolve_ref_non_internal_returns_empty(esi_schema: dict[str, Any]):
    """Non-internal refs (not starting with #/) should return an empty dict."""
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    ref = "https://example.com#/components/schemas/AllianceID"
    resolved = client._resolve_ref(ref)

    assert resolved == {}


def test_resolve_internal_ref_valid_path(esi_schema: dict[str, Any]):
    """Valid internal path parts should resolve to the referenced mapping."""
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    parts = ["components", "parameters", "Tenant"]
    resolved = client._resolve_internal_ref(parts)

    assert isinstance(resolved, dict)
    assert resolved["name"] == "X-Tenant"
    assert resolved["in"] == "header"


def test_resolve_internal_ref_non_dict_leaf_returns_empty(esi_schema: dict[str, Any]):
    """If the targeted value is not a dict, resolver should return an empty dict."""
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    # This path ends at a non-dict leaf (a string 'integer'), so resolver should return {}
    parts = ["components", "schemas", "AllianceID", "type"]
    resolved = client._resolve_internal_ref(parts)

    assert resolved == {}
