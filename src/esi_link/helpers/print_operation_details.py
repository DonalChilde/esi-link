from esi_link.esi_schema import operation_accessors as OA
from esi_link.esi_schema.esi_api_protocol import IndexedOperation


def operation_details_table(indexed_operation: IndexedOperation) -> str:
    """Return a detailed string representation of a single operation."""
    lines = [
        f"Operation ID: {indexed_operation.operation_id}",
        f"Summary: {indexed_operation.summary}",
        f"Description: {indexed_operation.description}",
        f"HTTP Method: {indexed_operation.method}",
        f"Path: {indexed_operation.path}",
        f"Requires Auth: {'Yes' if indexed_operation.requires_auth else 'No'}",
        "Parameters:",
    ]

    for param in indexed_operation.parameters:
        lines.append(f"  - Name: {param.name}")
        lines.append(f"    In: {param.in_}")
        lines.append(f"    Required: {'Yes' if param.required else 'No'}")
        lines.append(f"    Description: {param.description}")
        if param.schema:
            lines.append(f"    Schema: {param.schema}")

    responses = indexed_operation.operation.get("responses", {})
    lines.append("Responses:")
    for status_code, response in responses.items():
        lines.append(f"  - Status Code: {status_code}")
        description = response.get("description", "No description")
        lines.append(f"    Description: {description}")
        content = response.get("content", {})
        if content:
            lines.append("    Content:")
            for mime_type, mime_info in content.items():
                lines.append(f"      - MIME Type: {mime_type}")
                schema = mime_info.get("schema")
                if schema:
                    lines.append(f"        Schema: {schema}")

    return "\n".join(lines)
