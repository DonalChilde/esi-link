from rich.console import Console
from rich.table import Table

from esi_link.v2.helpers.indexed_operation_helpers import (
    IndexedOperationSummary,
)


def display_operations_by_tag(
    summaries_by_tag: dict[str, list[IndexedOperationSummary]],
) -> None:
    """Display operation summaries grouped by tag in a nice table format using rich."""
    console = Console()
    for tag, summaries in summaries_by_tag.items():
        table = Table(title=f"Operations with tag: {tag}")
        table.add_column("Operation ID", style="cyan", no_wrap=True)
        table.add_column("Method", style="magenta")
        table.add_column("Description", style="green")
        table.add_column("Auth Required", style="red")
        for summary in summaries:
            auth_required_str = "Yes" if summary["auth_required"] else "No"
            table.add_row(
                summary["operation_id"],
                summary["method"],
                summary.get("description", "").replace("\n", "--"),
                auth_required_str,
            )
        console.print(table)
