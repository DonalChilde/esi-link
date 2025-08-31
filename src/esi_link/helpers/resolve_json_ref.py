"""Resolve internal json references."""

from typing import Any


# TODO make tests for this and use inplace of current implementation.
# TODO does the spec allow only returning dict?
def resolve_json_ref(spec: dict[str, Any], reference: str) -> dict[str, Any]:
    """Resolve a JSON reference (RFC 6901) to its definition in the spec."""
    if reference.startswith("#/"):
        # Resolve internal reference
        parts = reference[2:].split("/")
        obj = spec
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return {}
        return obj if isinstance(obj, dict) else {}
    return {}
