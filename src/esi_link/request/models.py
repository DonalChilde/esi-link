from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from pydantic import RootModel
from whenever import Instant

from esi_link.actions.models import Action, GroupAction
from esi_link.type_defs import Lang


@dataclass(slots=True, kw_only=True, frozen=True)
class Request:
    """Represents a single ESI request to be executed.

    Can be loaded from a file or created programmatically. The request_id is used to
    identify the request.

    Requests can be be contained in a RequestGroup, and the request_id is used
    to link the Request to its RuntimeRequest, and to the final Response.
    """

    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various 
        objects during the request lifecycle."""
    created_on: Instant = field(default_factory=Instant.now)
    """The timestamp of when the request was created. This is used for things like 
        determining the age of the request, or for saving response data to disk with a 
        filename that includes the creation date."""
    description: str | None = None
    """An optional description of the request. This is used for documentation purposes, 
        and can be used to provide context for the request when viewing it in a UI or in 
        logs."""
    operation_id: str
    """The operation ID of the request, corresponding to the operationId in the ESI 
        OpenAPI schema."""
    compatibility_date: str | None = None
    """Optional compatibility date for the request. If not provided, the latest schema
        will be used."""
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The path parameters for the request, if applicable. This is used to fill in the 
        path parameters in the URL template."""
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    """The query parameters for the request, if applicable. This is used to fill in the 
        query parameters in the URL template."""
    authorization_id: int | None = None
    """The Character ID to use for authentication, if applicable."""
    language: Lang = "en"
    """The language to use for the request, if applicable. This is used to set the 
        Accept-Language header in the request."""
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH 
        requests."""
    actions: list[Action] = field(default_factory=list[Action])

    def to_string(self, indent: int) -> str:
        """Return a string representation of the request with the specified indentation."""
        root_model = RequestRoot(self)
        json_str = root_model.model_dump_json(indent=indent)
        return json_str

    @classmethod
    def from_string(cls, json_str: str) -> Request:
        """Parse the request from a JSON string."""
        value = RequestRoot.model_validate_json(json_str).root
        return value


@dataclass(slots=True, kw_only=True, frozen=True)
class RequestGroup:
    """Represents a batch of ESI requests to be executed.

    Can be loaded from a file or created programatically. The group_id is used to
    identify the group, and can be used for things like saving response data to disk with
    a filename that includes the group_id.
    """

    created_on: Instant = field(default_factory=Instant.now)
    group_id: UUID
    description: str = ""
    requests: dict[UUID, Request]
    group_actions: list[GroupAction] = field(default_factory=list[GroupAction])

    def to_string(self, indent: int) -> str:
        """Return a string representation of the RequestGroup with the specified indentation."""
        root_model = RequestGroupRoot(self)
        json_str = root_model.model_dump_json(indent=indent)
        return json_str

    @classmethod
    def from_string(cls, json_str: str) -> RequestGroup:
        """Parse the RequestGroup from a JSON string."""
        value = RequestGroupRoot.model_validate_json(json_str).root
        return value


RequestRoot = RootModel[Request]
RequestGroupRoot = RootModel[RequestGroup]
