from textwrap import fill

from esi_link.esi_schema import operation_accessors as OA
from esi_link.esi_schema.esi_api import EsiApi


def operations_by_tag_table(api: EsiApi, max_width: int = 120) -> str:
    """
    Return available operations grouped by tag, sorted alphabetically inside each tag,
    and indicate if authorization is required (flag after operation id).

    Args:
        api (EsiApi): The OpenAPI client instance.

    Returns:
        str: A formatted string table of operations grouped by tag.
    """
    operations_by_tag = OA.operations_by_tag(api.indexed_operations)

    if not operations_by_tag:
        return "No operations found."

    lines: list[str] = []

    for tag in operations_by_tag.keys():
        # Tag header
        lines.append(f"\n{tag.upper()}")
        lines.append("=" * len(tag))

        # Find the maximum operation_id length for alignment
        max_op_id_length = max(len(op.operation_id) for op in operations_by_tag[tag])
        # Ensure minimum width for readability
        col_width = max(max_op_id_length, 25)

        # Table header
        lines.append(f"{'Operation ID':<{col_width + 2}} {'Auth':<6} Description")
        lines.append("-" * (max_width))

        # Operations
        for operation in operations_by_tag[tag]:
            auth_flag = "Yes" if operation.requires_auth else "No"
            # Some descriptions have newlines; replace with asterisk for single-line display
            description = operation.description.replace("\n", " * ")
            operation_line = f"{operation.operation_id:<{col_width + 2}} {auth_flag:<6} {description}"
            # make the line wrap if the description is too long
            operation_line = fill(
                operation_line,
                width=max_width,
                subsequent_indent=" " * (col_width + 10),
                break_long_words=False,
            )
            lines.append(operation_line)

    return "\n".join(lines)
