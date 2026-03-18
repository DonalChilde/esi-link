"""Helper functions for working with ESI schemas."""

from typing import Any

from whenever import Instant

from esi_link.v3.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.v3.models_and_protocols import IndexedEsiSchema, IndexedOperation


def from_raw_schema(
    raw_schema: dict[str, Any],
    download_date: str,
) -> IndexedEsiSchema:
    """Factory method to create an IndexedEsiSchema instance from a raw OpenAPI schema.

    Args:
        raw_schema: The raw OpenAPI schema as a dictionary.
        download_date: The date the schema was downloaded.

    Returns:
        An instance of IndexedEsiSchema.
    """
    download_date_instant = Instant.parse_iso(download_date)
    dereferenced_schema = resolve_internal_refs(raw_schema, raw_schema)

    operations: dict[str, IndexedOperation] = {}
    paths = dereferenced_schema.get("paths", {})
    for path, methods in paths.items():
        for method, operation in methods.items():
            operation_id = operation.get("operationId")
            if operation_id:
                operations[operation_id] = IndexedOperation(
                    method=method.upper(),
                    path=path,
                    operation=operation,
                )
    return IndexedEsiSchema(
        download_date=download_date_instant,
        esi_schema=dereferenced_schema,
        operations=operations,
        security_schemes=dereferenced_schema.get("components", {}).get(
            "securitySchemes", {}
        ),
        info=dereferenced_schema.get("info", {}),
        openapi=dereferenced_schema.get("openapi", ""),
        servers=dereferenced_schema.get("servers", []),
        tags=dereferenced_schema.get("tags", []),
    )
