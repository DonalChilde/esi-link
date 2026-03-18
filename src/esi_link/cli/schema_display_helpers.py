from rich.console import Console
from rich.table import Table

from esi_link.helpers.indexed_operation_summary import IndexedOperationSummary


def display_operations_by_tag(
    summaries_by_tag: dict[str, list[IndexedOperationSummary]],
) -> None:
    """Display operation summaries grouped by tag in a nice table format using rich."""
    console = Console()
    for tag, summaries in summaries_by_tag.items():
        table = Table(title=f"Operations with tag: {tag}")
        table.add_column("Operation ID", style="cyan", no_wrap=True)
        table.add_column("Method", style="magenta")
        table.add_column("Auth", style="red")
        table.add_column("Paged", style="yellow")
        table.add_column("Description", style="green")

        for summary in summaries:
            auth_required_str = "Yes" if summary["auth_required"] else "No"
            paged_str = "Yes" if summary["is_paged"] else "No"
            table.add_row(
                summary["operation_id"],
                summary["method"],
                auth_required_str,
                paged_str,
                summary.get("description", "").replace("\n", "--"),
            )
        console.print(table)
