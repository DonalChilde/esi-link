# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

import logging
from pathlib import Path
from uuid import uuid4

from rich.console import Console
from whenever import Instant

from esi_link.v2 import example_requests
from esi_link.v2.esi_schema import load_schema_store
from esi_link.v2.handler_manager import DummyHandlerManager
from esi_link.v2.logging_config import setup_logging
from esi_link.v2.models import EsiRequests, EsiResponse
from esi_link.v2.request_manager import EsiLink
from esi_link.v2.schema_manager import SchemaManager
from esi_link.v2.settings import get_settings

logger = logging.getLogger(__name__)
SCRIPT_NAME = "NOT_DEFINED"


def main() -> None:
    """Main entry point for the link_test script."""
    settings = get_settings()
    schema_manager = SchemaManager(settings=settings)
    schema = schema_manager.get_latest_schema()
    handler_manager = DummyHandlerManager()
    esi_link = EsiLink(
        settings=settings, schema=schema, handler_manager=handler_manager
    )
    requests = build_requests()
    responses = execute_requests(esi_link, requests)
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
        console.print(f"\tcache status: NOT_IMPLEMENTED")
        console.print(f"\thttp status: {response.http_response.status_code}")
        console.print(f"\trequest took NOT_IMPLEMENTED seconds")
        console.print(f"\tresource expires in: NOT_IMPLEMENTED seconds")
        if response.http_response:
            console.print(response.http_response.body, overflow="crop")


def build_requests() -> EsiRequests:
    """Build ESI requests for testing.

    This function creates an EsiRequests object containing a single ESI request
    for the GetStatus operation.

    Returns:
        EsiRequests: An object containing the constructed ESI requests.
    """
    status_request = example_requests.esi_status()
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
