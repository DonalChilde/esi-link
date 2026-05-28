"""Validation Models for ESI requests and request groups."""

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import RootModel
from whenever import Instant

from esi_link.rewrite.request.models import (
    Request,
    RequestGroup,
)
from esi_link.type_defs import Lang


@dataclass(slots=True, kw_only=True, frozen=True)
class ValidatedRequestAction:
    action_type: str
    action_parameters: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(slots=True, kw_only=True, frozen=True)
class ValidatedRequestGroupAction:
    action_type: str
    action_parameters: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(slots=True, kw_only=True, frozen=True)
class ValidatedRequest:
    """Represents a validated ESI request, ready to be executed.

    The path, query, and json body parameters are duplicated from the original Request,
    but are now validated and ready to be used for the actual HTTP request to ESI. This
    allows for manipulation of the parameters during validation without affecting the
    original Request object, which can be useful for ensuring that the params used match
    the program's expectations. e.g. page is a valid query parameter for a paged operation,
    but the program may want to set it to 1 if it's not provided in the original Request,
    and this way the original Request remains unchanged, while the ValidatedRequest has
    the page parameter set to 1 for use in the actual HTTP request to ESI.

    Additional fields are added to capture required info from the schema for the request,
    such as the path URL template, HTTP method, and whether the request is paged or cacheable.
    This allows for easy access to this information during the execution of the request,
    without needing to refer back to the original Request or the ESI schema.

    """

    # These fields are copied from the original Request, but are now validated and ready
    # to be used for the actual HTTP request to ESI.

    request_id: UUID = field(default_factory=uuid4)
    """The unique identifier for the request. This is used to link the request to various objects during the request lifecycle."""
    created_on: Instant = field(default_factory=Instant.now)
    """The timestamp of when the request was created. This is used for things like determining the age of the request, or for saving response data to disk with a filename that includes the creation date."""
    operation_id: str = "NOT_SET"
    """The operation ID of the request, corresponding to the operationId in the ESI OpenAPI schema."""
    compatibility_date: str | None = None
    """Optional compatibility date for the request. If not provided, the latest schema will be used."""
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
    actions_after_response: list[ValidatedRequestAction] = field(
        default_factory=list[ValidatedRequestAction]
    )
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""

    # These fields are added to capture required info from the schema for the request,
    # such as the path URL template, HTTP method, and whether the request is paged or cacheable.
    path_url_template: str = ""
    """The URL template for the path."""
    method: Literal[
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "NOT_SET"
    ] = "NOT_SET"
    """The HTTP method for the request."""
    is_paged: bool = False
    """Whether the request is paged or not, based on the presence of pagination-related parameters in the operation schema."""
    is_cached: bool = False
    """Whether the request is cacheable or not, based on the HTTP method of the operation."""
    is_authentication_required: bool = False
    """Whether the request requires authentication or not, based on the presence of security requirements in the operation schema."""


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedRequestValidation:
    request: Request
    """The original request that failed validation."""
    errors: tuple[str, ...]
    """A list of error messages describing the validation failures."""


@dataclass(slots=True, kw_only=True, frozen=True)
class ValidatedRequestGroup:
    """Represents a validated batch of ESI requests, ready to be executed."""

    # These fields are copied from the original RequestGroup, but are now validated and
    # ready to be executed. The requests field is now a dictionary of ValidatedRequest,
    # and an additional field is added to capture any failed request validations, which
    # is a dictionary of FailedRequestValidation.
    created_on: Instant
    group_id: UUID
    description: str
    requests: dict[UUID, ValidatedRequest] = field(
        default_factory=dict[UUID, ValidatedRequest]
    )
    response_actions: list[ValidatedRequestGroupAction] = field(
        default_factory=list[ValidatedRequestGroupAction]
    )
    # save_directory_template: str | None = None
    # """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    # save_filename_template: str | None = None
    # """The filename template to save the response group data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""

    failed_request_validations: dict[UUID, FailedRequestValidation] = field(
        default_factory=dict[UUID, FailedRequestValidation]
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedRequestGroupValidation:
    request_group: RequestGroup
    """The original request group that failed validation."""
    errors: tuple[str, ...]
    """A list of error messages describing the validation failures."""


FailedRequestValidationRoot = RootModel[FailedRequestValidation]
