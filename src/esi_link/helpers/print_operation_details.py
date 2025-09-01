from typing import Any

from esi_link.esi_schema.eve_openapi_protocol import OperationSchema


def format_operation_details(op_schema: OperationSchema) -> str:
    """
    Return a formatted string for one operation, its description, and a table of request parameters.

    Args:
        op_schema (OperationSchema): The operation schema object.

    Returns:
        str: Formatted string with operation details and parameter table.
    """
    lines: list[str] = []
    lines.append(f"Operation: {op_schema.operation_id}")
    desc = op_schema.schema.get("description", "").strip() or "(no description)"
    lines.append(f"Description: {desc}")
    lines.append("")
    lines.append("Request Parameters:")
    lines.append(f"{'Name':<20} {'Group':<10} {'Type':<10} {'Required':<8} Description")
    lines.append("-" * 80)
    for param in op_schema.schema.get("parameters", []):
        name = param.get("name", "")
        group = param.get("in", "")
        typ = param.get("schema", {}).get("type", "")
        required = str(param.get("required", False))
        pdesc = param.get("description", "").strip() or "(no description)"
        lines.append(f"{name:<20} {group:<10} {typ:<10} {required:<8} {pdesc}")
    return "\n".join(lines)


# Usage example:
# details = format_operation_details(op_schema)
# print(details)
