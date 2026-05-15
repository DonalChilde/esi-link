import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from types import TracebackType
from typing import Any, Literal, Protocol, Self, cast
from uuid import UUID, uuid4

import aiohttp
from whenever import Instant

from esi_link.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.type_defs import Lang

logger = logging.getLogger(__name__)


# TODO
# - flesh out models
# - add debug models? failure models?
# flow is: Request -> ValidatedRequest -> RuntimeRequest -> RuntimeResponse -> Response
# can we skip runtimerequest stage? do it all in validated request?
def _get_current_instant() -> Instant:
    """Factory function to get current instant for default values.

    This function is used as a default_factory to avoid Pydantic issue with using a
    non-callable default for a non-serializable type.

    Returns:
        Current instant in time.
    """
    return Instant.now()


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
    operation_id: str
    """The operation ID of the request, corresponding to the operationId in the ESI OpenAPI schema."""
    compatibility_date: str | None = None
    """Optional compatibility date for the request. If not provided, the latest schema will be used."""
    after: int | None = None
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
    lang: Lang = "en"
    """The language to use for the request, if applicable. This is used to set the Accept-Language header in the request."""
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH requests."""
    save_directory_template: str | None = None
    """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    save_filename_template: str | None = None
    """The filename template to save the response data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""


@dataclass(slots=True, kw_only=True, frozen=True)
class ValidatedRequest(Request):
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

    path_url_template: str
    """The URL template for the path."""
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    """The HTTP method for the request."""
    is_paged: bool = False
    """Whether the request is paged or not, based on the presence of pagination-related parameters in the operation schema."""
    is_cached: bool = False
    """Whether the request is cacheable or not, based on the HTTP method of the operation."""


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedRequestValidation:
    request: Request
    """The original request that failed validation."""
    errors: list[str]
    """A list of error messages describing the validation failures."""


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeRequest: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class RequestGroup:
    """Represents a batch of ESI requests to be executed.

    Can be loaded from a file or created programmatically. The group_id is used to
    identify the group, and can be used for things like saving response data to disk with
    a filename that includes the group_id.
    """

    created_on: Instant = field(default_factory=_get_current_instant)
    group_id: UUID
    description: str = ""
    requests: dict[UUID, Request]
    save_directory_template: str | None = None
    """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    save_filename_template: str | None = None
    """The filename template to save the response group data to, if applicable. If not provided, but a save_directory_template is provided, a default filename will be used."""


@dataclass(slots=True, kw_only=True, frozen=True)
class ValidatedRequestGroup(RequestGroup):
    """Represents a validated batch of ESI requests, ready to be executed."""

    validated_requests: dict[UUID, ValidatedRequest] = field(
        default_factory=dict[UUID, ValidatedRequest]
    )
    failed_request_validations: dict[UUID, FailedRequestValidation] = field(
        default_factory=dict[UUID, FailedRequestValidation]
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class FailedRequestGroupValidation:
    request_group: RequestGroup
    """The original request group that failed validation."""
    errors: list[str]
    """A list of error messages describing the validation failures."""


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeRequestGroup: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeResponse: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class RuntimeResponseGroup: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class Response: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseGroup: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class HttpResponse: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class SchemaOperation:
    """Represents an operation defined in the ESI OpenAPI schema.

    This class is used to store the details of an operation, including the path, method,
    operation ID, and the full operation schema. This allows for easy access to the
    details of each operation when generating documentation or validating requests.

    equivalent to the combination of the path, method, and operation object from the OpenAPI schema.
    "paths":<path>:<method>:<operation_schema> from the OpenAPI schema.
    """

    path: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    operation_schema: dict[str, Any]

    @property
    def operation_id(self) -> str:
        """Extract the operation ID from the operation object."""
        return self.operation_schema.get("operationId", "")

    @property
    def tags(self) -> list[str]:
        """Extract the tags from the operation object, if present."""
        return [tag for tag in self.operation_schema.get("tags", [])]

    @property
    def description(self) -> str:
        """Extract the description from the operation object, if present."""
        return self.operation_schema.get("description", "")

    @property
    def path_and_query_parameters(self) -> list[dict[str, Any]]:
        """Extract all parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") in {"path", "query"}
        ]

    @property
    def path_params(self) -> list[dict[str, Any]]:
        """Extract the path parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "path"
        ]

    @property
    def query_params(self) -> list[dict[str, Any]]:
        """Extract the query parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "query"
        ]

    @property
    def header_params(self) -> list[dict[str, Any]]:
        """Extract the header parameters from the operation object, if present."""
        return [
            deepcopy(param)
            for param in self.operation_schema.get("parameters", [])
            if param.get("in") == "header"
        ]

    @property
    def responses(self) -> dict[str, Any]:
        """Extract the response schema from the operation object, if present."""
        success_responses = (
            self.operation_schema.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        return deepcopy(success_responses)

    @property
    def request_body(self) -> dict[str, Any] | None:
        """Extract the request body from the operation object, if present."""
        return deepcopy(self.operation_schema.get("requestBody"))

    @property
    def auth_required(self) -> bool:
        """Determine if the operation requires authentication based on the presence of security requirements."""
        return "security" in self.operation_schema and bool(
            self.operation_schema["security"]
        )

    @property
    def is_paged(self) -> bool:
        """Determine if the operation is paged based on the presence of pagination-related parameters."""
        for param in self.query_params:
            if param.get("name") in {"page"}:
                return True
        return False

    @property
    def is_cached(self) -> bool:
        """Determine if the operation is cacheable."""
        if self.method in {"GET", "get"}:
            return True
        return False

    @property
    def summary(self) -> str | None:
        """Extract the summary from the operation object, if present."""
        return self.operation_schema.get("summary")

    @property
    def x_values(self) -> list[dict[str, Any]]:
        """Extract the x-values from the operation object, if present."""
        x_list: list[dict[str, Any]] = []
        for key, value in self.operation_schema.items():
            if key.startswith("x-"):
                x_list.append({key: deepcopy(value)})
        return x_list


@dataclass(slots=True, kw_only=True, frozen=True)
class EsiSchema:
    """Represents the ESI OpenAPI schema and its associated metadata.

    For ease of access to the details of the schema.
    """

    dereferenced_schema: dict[str, Any]

    def __post_init__(self) -> None:
        """Ensure that the schema is valid."""
        if "openapi" not in self.dereferenced_schema:
            raise ValueError("Invalid schema: missing 'openapi' field")

    @classmethod
    def from_raw_schema(cls, raw_schema: dict[str, Any]) -> Self:
        """Factory method to create an EsiSchema instance from a raw OpenAPI schema.

        This method will resolve all internal JSON references in the schema, so that
        the resulting EsiSchema instance contains a fully dereferenced schema for easy
        access to all the details of the operations defined in the schema.

        Args:
            raw_schema: The raw OpenAPI schema as a dictionary.

        Returns:
            An instance of EsiSchema with the dereferenced schema.
        """
        dereferenced_schema = resolve_internal_refs(raw_schema, raw_schema)
        return cls(dereferenced_schema=dereferenced_schema)

    @property
    def operation_ids(self) -> set[str]:
        """Extract the set of operation IDs from the schema."""
        operation_ids: set[str] = set()
        paths = self.dereferenced_schema.get("paths", {})
        for _path, methods in paths.items():
            for _method, operation in methods.items():
                operation_id = operation.get("operationId")
                if operation_id:
                    operation_ids.add(operation_id)
        return operation_ids

    @property
    def operations(self) -> dict[str, SchemaOperation]:
        """Extract the operations from the schema and return them as a dictionary mapping operation IDs to SchemaOperation instances."""
        operations: dict[str, SchemaOperation] = {}
        operation_ids = self.operation_ids
        for operation_id in operation_ids:
            operation = self.get_operation_by_id(operation_id)
            if operation:
                operations[operation_id] = operation
        return operations

    def get_operation_by_id(self, operation_id: str) -> SchemaOperation | None:
        """Get a SchemaOperation by its operation ID."""
        paths = self.dereferenced_schema.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if operation.get("operationId") == operation_id:
                    return SchemaOperation(
                        path=path,
                        method=method.upper(),
                        operation_schema=deepcopy(operation),
                    )
        return None

    @property
    def operation_id_by_tag(self) -> dict[str, list[str]]:
        """Extract a mapping of tags to operation IDs from the schema."""
        tag_mapping: dict[str, list[str]] = {}
        paths = self.dereferenced_schema.get("paths", {})
        for _path, methods in paths.items():
            for _method, operation in methods.items():
                operation_id = operation.get("operationId")
                tags = operation.get("tags", [])
                if not tags:
                    tags = ["untagged"]
                for tag in tags:
                    if tag not in tag_mapping:
                        tag_mapping[tag] = []
                    if operation_id:
                        tag_mapping[tag].append(operation_id)
        # sort the tags alphabetically, and the operation IDs within each tag alphabetically as well
        tag_mapping = {
            tag: sorted(operation_ids)
            for tag, operation_ids in sorted(tag_mapping.items())
        }
        return tag_mapping

    @property
    def compatibility_date(self) -> str:
        """Get the compatibility date of the ESI schema from the info section."""
        return self.version

    @property
    def version(self) -> str:
        """Get the version of the ESI schema based on the compatibility date."""
        version = cast(str, self.dereferenced_schema["info"]["version"])
        return version

    @property
    def base_url(self) -> str:
        """Get the base URL for the ESI API from the servers section of the schema."""
        return self.dereferenced_schema["servers"][0]["url"]


@dataclass(slots=True, kw_only=True, frozen=True)
class StoredSchema:
    """Represents a stored ESI schema, including the raw schema and the date it was downloaded."""

    esi_schema: EsiSchema
    download_date: Instant


@dataclass(slots=True, kw_only=True, frozen=True)
class AvailableSchema:
    """Represents an available ESI schema in the SchemaManager.

    Available schemas are returned as a list of AvailableSchema, where each instance contains:
        - compatibility_date (str): The compatibility date of the schema.
        - timestamp (int): The timestamp of the schema download.
        - datetime (str): The download date and time of the schema as an ISO 8601 string.
    """

    compatibility_date: str
    timestamp: int
    datetime: str
