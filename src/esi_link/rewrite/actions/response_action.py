from esi_link.rewrite.actions.protocols import (
    CONTEXT,
    ActionProtocol,
    GroupActionProtocol,
)
from esi_link.rewrite.response.models import (
    Response,
    ResponseGroup,
)
from esi_link.rewrite.runtime.models import (
    FailedRuntimeResponse,
)
from esi_link.rewrite.validation.models import (
    FailedRequestValidation,
    ValidatedRequestAction,
    ValidatedRequestGroupAction,
)


def get_response_action_instance(action: ValidatedRequestAction) -> ActionProtocol:
    """Instance an action based on the action type and parameters in the ValidatedRequestAction."""
    # Implement the logic to retrieve the action instance from the store based on the action type
    # and parameters in the ValidatedRequestAction
    pass


def get_group_response_action_instance(
    action: ValidatedRequestGroupAction,
) -> GroupActionProtocol:
    """Instance a group action based on the action type and parameters in the ValidatedRequestGroupAction."""
    # Implement the logic to retrieve the group action instance from the store based on the action type
    # and parameters in the ValidatedRequestGroupAction
    pass


async def do_response_action(
    action: ActionProtocol,
    response: Response,
    context: CONTEXT,
) -> tuple[Response, CONTEXT]:
    """Do the response action with the given response and context.

    Return the possibly modified response and context.

    Note that actions are only performed on successful responses. To handle actions on
    failed responses, use group actions, which have access to the entire response group
    and can perform actions on failed responses as well.
    """
    response, context = action.do_action(response, context)
    return response, context


async def do_group_response_action(
    action: GroupActionProtocol, response_group: ResponseGroup, context: CONTEXT
) -> tuple[ResponseGroup, CONTEXT]:
    """Do the group response action with the given response group and context, and return the possibly modified response group and context."""
    # Implement the logic for handling the group response action here
    return response_group, context
