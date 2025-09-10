from esi_link.esi_schema.esi_api import EsiApi

# TODO use operation accessors where possible


def format_operations_by_tag_string(api: EsiApi) -> str:
    """
    Return available operations grouped by tag, sorted alphabetically inside each tag,
    and indicate if authorization is required (flag after operation id).

    Args:
        api (EveOpenApi): The OpenAPI client instance.

    Returns:
        str: Formatted string of operations grouped by tag.
    """
    tag_map: dict[str, list[tuple[str, str, str]]] = {}
    for op_schema in api.indexed_operations.values():
        tags = op_schema.operation.get("tags", [])
        description = (
            op_schema.operation.get("description", "").strip() or "(no description)"
        )
        description = description.replace("\n", " ")
        requires_auth = bool(op_schema.operation.get("security"))
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
