"""TypedDict models for ESI schema components.

NOTE Not currently in use.
"""

from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel

# openapi 3.1 specification
# https://swagger.io/specification/


class TypeSchema(TypedDict):
    type: Literal["string", "number", "integer", "boolean", "array", "object"]
    format: str
    description: NotRequired[str]


class Parameter(TypedDict):
    name: str
    in_: Literal["query", "path", "header", "cookie"]
    description: str
    required: bool
    schema: TypeSchema
    deprecated: NotRequired[bool]
    allowEmptyValue: NotRequired[bool]


class Operation(BaseModel):
    tags: list[str]
    summary: str
    description: str
    operationId: str
    parameters: list[dict[str, Any]]
    requestBody: dict[str, Any]
    responses: dict[str, Any]
    callbacks: dict[str, Any]
    deprecated: bool


class PathItem(TypedDict):
    ref: str
    summary: str
    description: str


class License(TypedDict):
    name: str
    url: str
    identifier: str


class Contact(TypedDict):
    name: str
    url: str
    email: str


class Info(TypedDict):
    title: str
    description: str
    version: str
    summary: str
    termsOfService: str
    contact: Contact
    license: License


class OpenApi(TypedDict):
    openapi: str
    info: Info
    paths: dict[str, dict[str, dict[str, Any]]]
    components: dict[str, Any]
