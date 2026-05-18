from uuid import UUID

from esi_link.simplified_models import (
    FailedRequestValidation,
    FailedRuntimeResponse,
    ResponseGroup,
    ResponseGroupAction,
    RuntimeResponse,
    RuntimeResponseAction,
)


async def do_response_action(
    action: RuntimeResponseAction,
    response: RuntimeResponse | FailedRuntimeResponse,
) -> RuntimeResponse | FailedRuntimeResponse:
    # Implement the logic for handling the response action here
    # get action instance from store
    # execute action with response as input
    # return possibly modified response if the action modifies the response.
    ...


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
    ...
