from typing import Any, TypedDict

# https://swagger.io/specification/


class Operation(TypedDict):
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
