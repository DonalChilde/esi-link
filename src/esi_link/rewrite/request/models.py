from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from whenever import Instant

from esi_link.rewrite.execution.models import HttpResponse
from esi_link.rewrite.runtime.models import (
    RequestGroupMetrics,
    RuntimeRequest,
    RuntimeResponseAction,
)
from esi_link.type_defs import Lang

# TODO split this to request and response models, and move to separate files. This file is getting a bit large, and the request and response models are somewhat distinct.


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseGroupAction:
    """Represents an action to be taken after receiving a group of responses."""

    action_type: str
    action_parameters: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(slots=True, kw_only=True, frozen=True)
class Request:
    """Represents a single ESI request to be executed.

    Can be loaded from a file or created programmatically. The request_id is used to
    identify the request.

    Requests can be be contained in a RequestGroup, and the request_id is used
    to link the Request to its RuntimeRequest, and to the final Response.
    """

    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various objects during the request lifecycle."""
    created_on: Instant = field(default_factory=Instant.now)
    """The timestamp of when the request was created. This is used for things like determining the age of the request, or for saving response data to disk with a filename that includes the creation date."""
    operation_id: str
    """The operation ID of the request, corresponding to the operationId in the ESI OpenAPI schema."""
    compatibility_date: str | None = None
    """Optional compatibility date for the request. If not provided, the latest schema will be used."""
    at_or_after: int | None = None
    """Used with compatibility date. Optional timestamp to refine compatibility date selection. If provided, the schema with the compatibility date that was downloaded after the provided timestamp will be used."""
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The path parameters for the request, if applicable. This is used to fill in the path parameters in the URL template."""
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The query parameters for the request, if applicable. This is used to fill in the query parameters in the URL template."""
    authorization_id: int | None = None
    """The Character ID to use for authentication, if applicable."""
    language: Lang = "en"
    """The language to use for the request, if applicable. This is used to set the Accept-Language header in the request."""
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH requests."""
    actions_after_response: list[RuntimeResponseAction] = field(
        default_factory=list[RuntimeResponseAction]
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class RequestGroup:
    """Represents a batch of ESI requests to be executed.

    Can be loaded from a file or created programmatically. The group_id is used to
    identify the group, and can be used for things like saving response data to disk with
    a filename that includes the group_id.
    """

    created_on: Instant = field(default_factory=Instant.now)
    group_id: UUID
    description: str = ""
    requests: dict[UUID, Request]
    response_actions: list[ResponseGroupAction] = field(
        default_factory=list[ResponseGroupAction]
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class Response:
    http_response: HttpResponse
    runtime_request: RuntimeRequest


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseGroup:
    group_id: UUID
    description: str = ""
    responses: dict[UUID, Response] = field(default_factory=dict[UUID, Response])
    metrics: RequestGroupMetrics = field(default_factory=RequestGroupMetrics)
