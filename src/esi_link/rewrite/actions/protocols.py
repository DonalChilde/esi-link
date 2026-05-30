from typing import Any, Protocol

from esi_link.rewrite.response.models import Response, ResponseGroup

type CONTEXT = dict[str, Any]


class ActionProtocol(Protocol):
    """Protocol for actions that can be executed after receiving a response for a request."""

    def do_action(
        self,
        response: Response,
        context: CONTEXT,
    ) -> tuple[Response, CONTEXT]:
        """Execute the action with the given response."""
        ...


class GroupActionProtocol(Protocol):
    """Protocol for actions that can be executed after receiving a group of responses."""

    def do_action(
        self, response_group: ResponseGroup, context: CONTEXT
    ) -> tuple[ResponseGroup, CONTEXT]:
        """Execute the action with the given responses."""
        ...
