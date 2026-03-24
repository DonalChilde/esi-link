from rich.console import Console

from esi_link.handlers.response_group.helpers import make_response_group_summary
from esi_link.models_and_protocols import ResponseGroup


def display_response_group_summary(
    response_group: ResponseGroup, console: Console
) -> None:
    """Display a summary of a ResponseGroup."""
    summary = make_response_group_summary(response_group)
    console.print(f"Request Group ID: {summary.request_group_id}")
    console.print(f"Group Duration (seconds): {summary.group_duration_seconds:.4f}")
    console.print(f"Number of Responses: {summary.num_responses}")
    console.print(f"Responses with Errors: {summary.responses_with_errors}")
    console.print(f"Responses that Hit Cache: {summary.responses_hit_cache}")
    console.print(f"Responses that Used Cache: {summary.responses_cache_action_used}")
    console.print(
        f"Responses that added to Cache: {summary.responses_cache_action_new}"
    )
    console.print(
        f"Responses that updated Cache with 304: {summary.responses_cache_action_update_304}"
    )
