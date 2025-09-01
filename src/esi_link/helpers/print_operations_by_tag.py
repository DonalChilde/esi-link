from esi_link.esi_schema.eve_openapi import EveOpenApi


def get_operations_by_tag_string(api: EveOpenApi) -> str:
    """
    Return available operations grouped by tag, sorted alphabetically inside each tag,
    and indicate if authorization is required (flag after operation id).

    Args:
        api (EveOpenApi): The OpenAPI client instance.

    Returns:
        str: Formatted string of operations grouped by tag.
    """
    tag_map: dict[str, list[tuple[str, str, str]]] = {}
    for op_schema in api.by_operation_id.values():
        tags = op_schema.schema.get("tags", [])
        description = (
            op_schema.schema.get("description", "").strip() or "(no description)"
        )
        requires_auth = bool(op_schema.schema.get("security"))
        auth_flag = "[auth]" if requires_auth else ""
        for tag in tags:
            tag_map.setdefault(tag, []).append(
                (op_schema.operation_id, auth_flag, description)
            )

    lines: list[str] = []
    for tag in sorted(tag_map):
        lines.append(f"{tag}")
        for operation_id, auth_flag, desc in sorted(
            tag_map[tag], key=lambda x: x[0].lower()
        ):
            lines.append(f"  {operation_id} {auth_flag}: {desc}")
        lines.append("")  # Blank line between tags
    return "\n".join(lines)


# Usage example:
# api = EveOpenApi.from_schema_store(schema_store)
# output = get_operations_by_tag_string(api)
# print(output)
