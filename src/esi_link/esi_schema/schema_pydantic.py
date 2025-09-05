"""Pydantic models for ESI schema components.

NOTE Not sure if this is a valid pursuit, as the OpenAPI schema is complex and may not map cleanly to Pydantic models.
Not currently in use.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Parameter(BaseModel):
    name: str
    in_: str = Field(..., alias="in")
    required: bool = False
    schema_: Optional[dict[str, Any]] = Field(None, alias="schema")
    description: Optional[str] = None
    example: Optional[Any] = None

    model_config = ConfigDict(extra="forbid")


class TypeDef(BaseModel):
    type_: Optional[
        Literal["string", "integer", "number", "boolean", "array", "object"]
    ] = Field(None, alias="type")


class JsonContent(BaseModel):
    items: Optional[dict[str, Any]] = None
    """When type is array"""
    properties: Optional[dict[str, dict[str, Any]]] = None
    """When type is object"""
    format_: Optional[str] = Field(None, alias="format")
    """When returning single simple type, e.g. number. see PostCharactersCharacterIdCspa"""
    type_: Optional[
        Literal["string", "integer", "number", "boolean", "array", "object"]
    ] = Field(None, alias="type")
    # required: Optional[list[str]] = None
    unique_items: Optional[bool] = Field(None, alias="uniqueItems")
    examples: Optional[dict[str, Any]] = None
    description: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class JsonContentSchema(BaseModel):
    schema_: Optional[JsonContent] = Field(None, alias="schema")


class Content(BaseModel):
    application_json: JsonContentSchema = Field(..., alias="application/json")


class Response(BaseModel):
    description: Optional[str] = None
    content: Optional[Content] = None
    headers: dict[str, Any] = {}

    model_config = ConfigDict(extra="forbid")


class Responses(BaseModel):
    a_200: Optional[Response] = Field(None, alias="200")
    a_201: Optional[Response] = Field(None, alias="201")
    a_204: Optional[Response] = Field(None, alias="204")
    default: dict[str, Any] = {}

    model_config = ConfigDict(extra="forbid")


class Operation(BaseModel):
    operation_id: str = Field(..., alias="operationId")
    description: Optional[str] = None
    parameters: list[Parameter] = []
    responses: Responses
    request_body: Optional[dict[str, Any]] = Field(None, alias="requestBody")
    security: Optional[list[dict[str, list[str]]]] = None
    summary: str = ""
    tags: list[str] = []
    x_compatibility_date: str = Field("", alias="x-compatibility-date")
    x_cache_age: Optional[int] = Field(None, alias="x-cache-age")
    x_required_roles: Optional[list[str]] = Field(None, alias="x-required-roles")

    model_config = ConfigDict(extra="forbid")


class OperationSchema(BaseModel):
    operation_id: str
    method: str
    path: str
    operation: Operation
