from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class Request(BaseModel): ...


class RequestGroup(BaseModel): ...


class Response(BaseModel): ...


class ResponseGroup(BaseModel): ...


@dataclass
class RuntimeRequest: ...


@dataclass
class RuntimeRequestGroup: ...


@dataclass
class ResponseHandlerConfig: ...


@dataclass
class ResponseGroupHandlerConfig: ...


class CachedResponseStatus(StrEnum): ...


@dataclass
class CachedResponse: ...


@dataclass
class HttpResponse: ...


@dataclass(slots=True)
class GeneratedUrlInfo:
    """Represents the generated URL information for an ESI request."""

    path_url: str
    cache_url: str
    cache_key: UUID
