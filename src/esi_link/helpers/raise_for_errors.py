import logging

from esi_link.errors import EsiLinkError
from esi_link.models_and_protocols import Response

logger = logging.getLogger(__name__)


def raise_for_network_errors(response: Response) -> None:
    """Raises an EsiLinkError if the response contains an HTTP error or no response at all.

    EsiLink traps network exceptions to prevent one failed request from crashing the entire
    batch. This function checks for those exceptions and also verifies that a response was
    received. If an error is detected, it logs the details and raises an EsiLinkError with
    a descriptive message.

    After a batch of requests is executed, you can call this function for each response
    to ensure that any issues are surfaced and handled appropriately in your application logic.
    """
    if response.http_response is None:
        logger.error(
            "No HTTP response received for operation \n%s",
            response.model_dump_json(indent=2),
        )
        raise EsiLinkError(
            f"Failed to get a response for operation {response.request.operation_id}."
        )
    if response.http_response.status_code > 399:
        status_code = response.http_response.status_code
        status_text = response.http_response.body_text
        logger.error(
            "HTTP error for operation %s\n%s",
            response.request.operation_id,
            response.model_dump_json(indent=2),
        )
        raise EsiLinkError(
            f"HTTP error for operation {response.request.operation_id}: status code {status_code} url: {response.http_response.url}, body: {status_text}"
        )


def raise_for_handler_errors(response: Response) -> None:
    """Raises an EsiLinkError if the response contains an error from a handler.

    This function checks the response for any errors that may have occurred during the
    processing of the request by a handler. If an error is detected, it logs the details
    and raises an EsiLinkError with a descriptive message.

    After processing a batch of requests, you can call this function for each response to
    ensure that any issues from handlers are surfaced and handled appropriately in your
    application logic.
    """
    if response.handler_exception_messages:
        logger.error(
            "Handler error for operation %s,%s\n%s",
            response.request.operation_id,
            response.handler_exception_messages,
            response.request.model_dump_json(indent=2),
        )
        raise EsiLinkError(
            f"Handler error for operation {response.request.operation_id}: {response.handler_exception_messages}"
        )
