# from dataclasses import dataclass, field
# from typing import Any, Optional
# from uuid import UUID

# from pydantic import BaseModel
# from whenever import Instant

# from esi_link.models import EsiRequest, ResponseContext


# @dataclass(slots=True)
# class HttpRequest:
#     method: str
#     url: str
#     is_paged: bool
#     ctx: ResponseContext
#     esi_request: EsiRequest
#     cache_key: Optional[UUID] = None
#     """The cache key UUID, built from the EsiRequest. None if caching is not used."""
#     app_handlers: list["ResponseHandlerProtocol"] = field(
#         default_factory=list["ResponseHandlerProtocol"]
#     )
#     """App level handlers to process the response. These are run before any request level handlers."""
#     user_handlers: list["ResponseHandlerProtocol"] = field(
#         default_factory=list["ResponseHandlerProtocol"]
#     )
#     """Request level handlers to process the response. These are run after any app level handlers."""
#     headers: dict[str, str] = field(default_factory=dict[str, str])
#     """App level headers to include in the request. These are merged with any request level headers."""
#     timeout: int = 10
#     page_number: int = 0
#     """The page number for paged requests."""


# class HttpResponse(BaseModel):
#     status_code: int
#     reason: str | None
#     url: str
#     headers: tuple[tuple[str, str | None], ...]
#     json_data: Any = None
#     etag: str = ""
#     last_modified: str = ""
#     expires: str = ""
#     completed_on: Instant = Field(default_factory=_get_current_instant)
