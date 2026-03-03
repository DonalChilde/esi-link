# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

import logging
from pathlib import Path
from uuid import uuid4

from rich.console import Console
from whenever import Instant

from esi_link import example_requests
from esi_link.logging_config import setup_logging
from esi_link.models import EsiRequests, EsiResponse
from esi_link.request_manager import EsiLink
from esi_link.response_handlers import HandlerManager
from esi_link.schema_manager import SchemaManager
from esi_link.settings import get_settings

logger = logging.getLogger(__name__)
SCRIPT_NAME = "NOT_DEFINED"


def main() -> None:
    """Main entry point for the link_test script."""
    settings = get_settings()
    schema_manager = SchemaManager(settings=settings)
    schema = schema_manager.get_latest_schema()
    handler_manager = HandlerManager()
    esi_link = EsiLink(
        settings=settings, schema=schema, handler_manager=handler_manager
    )
    output_dir = f"~/tmp/esi-link-scripts/{SCRIPT_NAME}"
    requests = build_requests(output_dir=output_dir)
    responses = execute_requests(esi_link, requests)
    save_responses(responses)
    display_responses(responses)


def execute_requests(esi_link: EsiLink, requests: EsiRequests) -> list[EsiResponse]:
    """Execute ESI requests asynchronously.

    This function takes an EsiRequests object containing multiple ESI requests,
    executes them asynchronously, and returns the responses.

    Args:
        esi_link (EsiLink): An instance of EsiLink to execute the requests.
        requests (EsiRequests): An object containing multiple ESI requests to be executed.

    Returns:
        list[EsiResponse]: A list containing the responses for the executed requests.
    """
    responses = esi_link.execute_requests(list(requests.requests.values()))
    return responses


def save_responses(responses: list[EsiResponse]) -> None:
    """Save the responses from ESI requests to files."""
    output_dir = Path.home() / "tmp" / "esi-link-scripts" / SCRIPT_NAME
    for response in responses:
        save_response(response, output_dir)


def save_response(response: EsiResponse, output_dir: Path) -> None:
    """Save an ESI response to a file.

    This function takes an EsiResponse object and saves its content to a file in the specified output directory.

    Args:
        response (EsiResponse): The ESI response to be saved.
        output_dir (Path): The directory where the response file will be saved.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    request_id = response.request.request_id
    operation_id = response.request.operation_id
    status_code = (
        response.http_response.status_code if response.http_response else "NO_RESPONSE"
    )
    output_file = (
        output_dir / f"response_{request_id}-{operation_id}-{status_code}.json"
    )

    with output_file.open("w") as f:
        f.write(response.model_dump_json(indent=2))


def display_responses(responses: list[EsiResponse]) -> None:
    """Display the responses from ESI requests.

    This function iterates through the responses contained in an EsiResponses object
    and prints the status code and request duration for each response.

    Args:
        responses (list[EsiResponse]): A list containing the responses for executed ESI requests.
    """
    console = Console()
    for response in responses:
        if response.http_response is None:
            console.print(
                f"No response for request ID {response.request.request_id}, operation ID {response.request.operation_id}"
            )
            console.print(f"\tError: {response.exception_messages}")
            continue
        console.print(f"Response for request ID {response.request.request_id}:")
        console.print(f"\trequest url: {response.http_response.url}")
        console.print(f"\tcache_key: {response.runtime_info.cache_key}")
        console.print(f"\tcache status: {response.metrics.cache_response_status}")
        console.print(f"\thttp status: {response.http_response.status_code}")
        console.print(
            f"\trequest took {response.metrics.task_completed - response.metrics.task_started:.4f} seconds"
        )
        if response.http_response and response.http_response.expires_at:
            expires_in = (
                response.http_response.expires_at - Instant.now()
            ).in_seconds()
            console.print(f"\tresource expires in: {expires_in:.4f} seconds")
        if response.http_response and response.http_response.ratelimit:
            console.print(
                f"\tratelimits -> group: {response.http_response.ratelimit.group}, "
                f"limit: {response.http_response.ratelimit.limit}, "
                f"remaining: {response.http_response.ratelimit.remaining}, "
                f"used: {response.http_response.ratelimit.used}"
            )
        if response.exception_messages:
            console.print(
                f"\tExceptions: {'\n\t\t'.join(response.exception_messages)}",
                style="red",
            )
        if response.http_response:
            console.print(response.http_response.body_text, overflow="ellipsis")


def build_requests(output_dir: str) -> EsiRequests:
    """Build ESI requests for testing.

    This function creates an EsiRequests object containing a single ESI request
    for the GetStatus operation.

    Returns:
        EsiRequests: An object containing the constructed ESI requests.
    """
    simple_handler_config = example_requests.simple_save_response(
        output_dir=output_dir, overwrite=False
    )
    status_request = example_requests.esi_status(handlers=[simple_handler_config])
    requests = EsiRequests(
        requests_id=uuid4(),
        created_on=Instant.now(),
        description="",
        requests={status_request.request_id: status_request},
    )
    return requests


if __name__ == "__main__":
    log_dir = Path(f"./logs/script_logs/{SCRIPT_NAME}").resolve()
    print(f"Logging to {log_dir}")
    setup_logging(log_dir)
    logger.info(f"Starting script {SCRIPT_NAME}")
    main()
