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


@dataclass(slots=True, kw_only=True, frozen=True)
class Request:
    """Represents a single ESI request to be executed.

    Can be loaded from a file or created programmatically. The request_id is used to
    identify the request.

    Requests can be be contained in a RequestGroup, and the request_id is used
    to link the Request to its RuntimeRequest, and to the final Response.
    """

    request_id: UUID = field(default_factory=uuid4)
    operation_id: str
    compatibility_date: str | None = None
    path_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    query_parameters: dict[str, str | int | float] = field(
        default_factory=dict[str, str | int | float]
    )
    authorization_id: int | None = None
    """The Character ID to use for authentication, if applicable."""
    lang: Lang = "en"
    json_body: Any | None = None
    """The JSON body of the request, if applicable. This is used for POST, PUT, PATCH requests."""
    save_directory: str | None = None
    """The directory to save the response data to, if applicable. If not provided, response data will not be saved to disk."""
    save_filename: str | None = None
    """The filename to save the response data to, if applicable. If not provided, but a save_directory is provided, a default filename will be used ."""


@dataclass
class ValidatedRequest: ...


@dataclass
class RuntimeRequest: ...


@dataclass
class RequestGroup: ...


@dataclass
class ValidatedRequestGroup: ...


@dataclass
class RuntimeRequestGroup: ...


@dataclass
class RuntimeResponse: ...


@dataclass
class RuntimeResponseGroup: ...


@dataclass
class Response: ...


@dataclass
class ResponseGroup: ...


@dataclass
class HttpResponse: ...
