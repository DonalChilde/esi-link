from uuid import UUID

from esi_link.esi_auth.models import (
    ResponseGroup,
)
from esi_link.rewrite.response.models import ResponseGroupAction
from esi_link.rewrite.runtime.models import (
    FailedRuntimeResponse,
    RuntimeResponse,
    RuntimeResponseAction,
)
from esi_link.rewrite.validation.models import FailedRequestValidation


async def do_response_action(
    action: RuntimeResponseAction,
    response: RuntimeResponse | FailedRuntimeResponse,
) -> RuntimeResponse | FailedRuntimeResponse:
    # Implement the logic for handling the response action here
    # get action instance from store
    # execute action with response as input
    # return possibly modified response if the action modifies the response.
    return response


async def do_group_response_action(
    action: ResponseGroupAction,
    response_group: ResponseGroup,
    failed_validations: dict[UUID, FailedRequestValidation],
    failed_runtime_responses: dict[UUID, FailedRuntimeResponse],
) -> tuple[
    ResponseGroup,
    dict[UUID, FailedRequestValidation],
    dict[UUID, FailedRuntimeResponse],
]:
    # Implement the logic for handling the group response action here
    return response_group, failed_validations, failed_runtime_responses
