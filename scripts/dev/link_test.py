# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

import asyncio
from pathlib import Path
from uuid import uuid4

from rich.console import Console

from esi_link import request_factory as RF
from esi_link.esi_link import EsiLink
from esi_link.helpers.esi_link_factory import esi_link_factory
from esi_link.logging_config import setup_logging
from esi_link.models import EsiRequests, EsiResponses

SCRIPT_NAME = "link_test"


def main() -> None:
    """Main entry point for the link_test script.

    Initializes an ESI link client, builds a collection of requests, executes those requests,
    and displays the resulting responses.

    Behavior:
    - Calls esi_link_factory() to obtain a configured ESI client or connector.
    - Calls build_requests() to prepare the request objects or payloads.
    - Calls execute_requests(esi_link, requests) to perform the requests and collect responses.
    - Calls display_responses(responses) to present the results (prints, logs, or UI rendering).

    Returns:
        None

    Exceptions:
        Any exceptions raised by esi_link_factory, build_requests, execute_requests, or
        display_responses are propagated to the caller.
    """
    esi_link = esi_link_factory()
    requests = build_requests()
    responses = execute_requests(esi_link, requests)
    display_responses(responses)


def execute_requests(esi_link: EsiLink, requests: EsiRequests) -> EsiResponses:
    """Execute ESI requests asynchronously.

    This function takes an EsiRequests object containing multiple ESI requests,
    executes them asynchronously, and returns the responses.

    Args:
        esi_link (EsiLink): An instance of EsiLink to execute the requests.
        requests (EsiRequests): An object containing multiple ESI requests to be executed.

    Returns:
        EsiResponses: An object containing the responses for the executed requests.
    """
    responses = asyncio.run(esi_link.execute_requests(requests))
    return responses


def display_responses(responses: EsiResponses) -> None:
    """Display the responses from ESI requests.

    This function iterates through the responses contained in an EsiResponses object
    and prints the status code and request duration for each response.

    Args:
        responses (EsiResponses): An object containing the responses for executed ESI requests.
    """
    console = Console()
    for key, response in responses.responses.items():
        if response.http_response is None:
            console.print(f"No response for request ID {key}")
            continue
        console.print(f"Response for request ID {key}:")
        console.print(f"\trequest url: {response.http_response.url}")
        console.print(f"\tcache status: {response.metrics.cache_check}")
        console.print(f"\thttp status: {response.http_response.status_code}")
        console.print(f"\trequest took {response.metrics.request_duration()} seconds")
        console.print(
            f"\tresource expires in: {response.http_response.expires_in()} seconds"
        )
        http_response = responses.responses[key].http_response
        if http_response:
            console.print(http_response.json_data, overflow="crop")

    # FIXME caching  is not returning the cached value. First call works, subsequent calls return a 304 but no data.


def build_requests() -> EsiRequests:
    """Build ESI requests for testing.

    This function creates an EsiRequests object containing a single ESI request
    for the GetStatus operation.

    Returns:
        EsiRequests: An object containing the constructed ESI requests.
    """
    request = RF.status()
    requests = EsiRequests(requests_id=uuid4(), requests={request.request_id: request})
    return requests


if __name__ == "__main__":
    log_dir = Path(f"./logs/script_logs/{SCRIPT_NAME}").resolve()
    print(f"Logging to {log_dir}")
    setup_logging(log_dir)
    main()
