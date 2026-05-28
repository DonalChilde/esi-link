# TODO split this to request and response models, and move to separate files. This file is getting a bit large, and the request and response models are somewhat distinct.


from dataclasses import dataclass, field
from typing import Any

from esi_link.rewrite.execution.models import HttpResponse
from esi_link.rewrite.runtime.models import RuntimeRequest


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseGroupAction:
    """Represents an action to be taken after receiving a group of responses."""

    action_type: str
    action_parameters: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(slots=True, kw_only=True, frozen=True)
class Response:
    http_response: HttpResponse
    runtime_request: RuntimeRequest
