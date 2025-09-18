"""Format operation details for documentation.

Needs to be refactored to be more modular.
Needs extensive rework to handle all the different schema types.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypedDict

from rich.json import JSON
from rich.panel import Panel
from rich.pretty import Pretty
from rich.table import Table

from esi_link.esi_schema import operation_accessors as OA
from esi_link.esi_schema.esi_api_protocol import IndexedOperation
from esi_link.helpers.indent_lines import indent_lines, prefixed_list_to_lines

# TODO rewrite this to use triple quote f strings
# TODO this need a lot of work to handle all the different schemas.
# A possible temp fix, is to have A cli option that outputs the raw schema for an operation.


def format_operation_details(op_schema: IndexedOperation) -> str:
    """
    Return a formatted string for one operation, its description, and tables of request parameters, response body parameters, and headers.

    Args:
        op_schema (OperationSchema): The operation schema object.

    Example:
        >>> format_operation_details("GetMarketsRegionIdOrders")
        ```text
        Operation: GetMarketsRegionIdOrders
        Tags: Market
        Description: Return a list of orders in a region
        Cache Age: 300
        Compatibility Date: 2020-01-01
        Authorization Required:
        - public

        Request Parameters:
        Name                 Group      Type       Required Description
        --------------------------------------------------------------------------------
        order_type           query      string     True     Filter buy/sell orders, return all orders by default. If you query without type_id, we always return both buy and sell orders (Possible values: buy, sell, all)
        page                 query      integer    False    Which page of results to return.
        region_id            path       integer    True     Return orders in this region
        type_id              query      integer    False    Return orders only for this type

        Response Body Parameters (container: array -> data: object):
        Name                 Group      Type       Required Description
        --------------------------------------------------------------------------------
        duration             body       integer    True     (no description)
        is_buy_order         body       boolean    True     (no description)
        issued               body       string     True     (no description)
        location_id          body       integer    True     (no description)
        min_volume           body       integer    True     (no description)
        order_id             body       integer    True     (no description)
        price                body       number     True     (no description)
        range                body       string     True     (no description)
        system_id            body       integer    True     The solar system this order was placed
        type_id              body       integer    True     (no description)
        volume_remain        body       integer    True     (no description)
        volume_total         body       integer    True     (no description)

        Headers:
        Name                 Type       Required Direction  Description
        --------------------------------------------------------------------------------
        Accept-Language      string     False    request    The language to use for the response.
        If-None-Match        string     False    request    The ETag of the previous request. A 304 will be returned if this matches the current ETag.
        X-Compatibility-Date string     True     request    The compatibility date for the request.
        X-Tenant             string     False    request    The tenant ID for the request.
        Cache-Control        string     False    response   Directives for caching mechanisms. It controls how the response can be cached, by whom, and for how long.
        ETag                 string     False    response   The ETag value of the response body. Use this with If-None-Match to check whether the resource has changed.
        Last-Modified        string     False    response   The last modified date of the response. Use this with If-Modified-Since to check whether the resource has changed.
        X-Pages              integer    False    response   The total number of pages in the result set.
        ```
    Returns:
        str: Formatted string with operation details and parameter tables.
    """
    lines: list[str] = []
    # lines.append(f"Operation: {op_schema.operation_id}")
    tag_group = op_schema.operation.get("tags", [])
    # lines.append(f"Tags: {', '.join(tag_group)}")
    desc = op_schema.operation.get("description", "").strip() or "(no description)"
    # lines.append(f"Description: {desc}")
    cache_age = op_schema.operation.get("x-cache-age", "Not Defined")
    # lines.append(f"Ca/che Age: {cache_age}")
    compatibility_date = op_schema.operation.get("x-compatibility-date", "Not Defined")
    # lines.append(f"Compatibility Date: {compatibility_date}")
    scopes: list[str] = []
    security: Any = op_schema.operation.get("security")
    if security and isinstance(security, list):
        for entry in security:  # type: ignore
            if "OAuth2" in entry:
                scopes = entry["OAuth2"]  # type: ignore
            else:
                scopes.append("public")

    top_section = f"""
    Operation: {op_schema.operation_id}
    Tags: {", ".join(tag_group)}
    Description: {desc}
    Cache Age: {cache_age}
    Compatibility Date: {compatibility_date}
    Authorization Required: 
    {prefixed_list_to_lines(scopes, prefix="- ", indent=2)}
    """
    # Authorization Required field
    # security: Any = op_schema.schema.get("security")
    # lines.append("Authorization Required:")
    # if security and isinstance(security, list):
    #     found = False
    #     for entry in security:  # type: ignore
    #         if "OAuth2" in entry:
    #             scopes = entry["OAuth2"]  # type: ignore
    #             if scopes:
    #                 for scope in scopes:  # type: ignore
    #                     lines.append(f"  - {scope}")
    #                 found = True
    #     if not found:
    #         lines.append("  - public")
    # else:
    #     lines.append("  - public")
    # lines.append("")
    # Request Parameters Table (excluding headers)
    # lines.append("Request Parameters:")
    # lines.append(f"{'Name':<20} {'Group':<10} {'Type':<10} {'Required':<8} Description")
    # lines.append("-" * 80)

    # Request Parameters
    req_params = request_parameters(op_schema.operation.get("parameters", []))
    params_as_lines = "\n".join(
        f"{param.name:<20} {param.group:<10} {param.type_:<10} {param.required:<8} {param.description}"
        for param in req_params
    )

    request_section = f"""
    Request Parameters:
    {f"{'Name':<20} {'Group':<10} {'Type':<10} {'Required':<8} Description"}
    {"-" * 80}
    {params_as_lines}
    """
    # Response Body Parameters Table
    content_schema = (
        op_schema.operation.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    container_type = content_schema.get("type", "Unknown")
    content_type = content_schema.get("items", {}).get("type", "Unknown")
    resp_params = response_body_parameters(content_schema.get("properties", {}))
    lines.append(
        f"Response Body Parameters (container: {container_type} -> data: {content_type}):"
    )
    lines.append(f"{'Name':<20} {'Group':<10} {'Type':<10} {'Required':<8} Description")
    lines.append("-" * 80)
    if container_type == "object":
        for name, prop in content_schema.get("properties", {}).items():
            group = "body"
            typ = prop.get("type", "")
            required = str(name in content_schema.get("required", []))
            pdesc = prop.get("description", "").strip() or "(no description)"
            lines.append(f"{name:<20} {group:<10} {typ:<10} {required:<8} {pdesc}")
    elif container_type == "array":
        items_schema = content_schema.get("items", {})
        # If items is an object, list its properties
        if items_schema.get("type") == "object":
            for name, prop in items_schema.get("properties", {}).items():
                group = "body"
                typ = prop.get("type", "")
                required = str(name in items_schema.get("required", []))
                pdesc = prop.get("description", "").strip() or "(no description)"
                lines.append(f"{name:<20} {group:<10} {typ:<10} {required:<8} {pdesc}")
        else:
            # If items is a primitive type
            typ = items_schema.get("type", "")
            lines.append(
                f"(array items)   body[item] {typ:<10} {'False':<8} (no description)"
            )
    lines.append("")
    # Headers Table (request and response)
    lines.append("Headers:")
    lines.append(
        f"{'Name':<20} {'Type':<10} {'Required':<8} {'Direction':<10} Description"
    )
    lines.append("-" * 80)
    # Request headers
    for param in op_schema.operation.get("parameters", []):
        if param.get("in") == "header":
            name = param.get("name", "")
            typ = param.get("schema", {}).get("type", "")
            required = str(param.get("required", False))
            direction = "request"
            pdesc = param.get("description", "").strip() or "(no description)"
            lines.append(f"{name:<20} {typ:<10} {required:<8} {direction:<10} {pdesc}")
    # Response headers
    response_headers = (
        op_schema.operation.get("responses", {}).get("200", {}).get("headers", {})
    )
    for name, param in response_headers.items():
        typ = param.get("schema", {}).get("type", "")
        required = str(param.get("required", False))
        direction = "response"
        pdesc = param.get("description", "").strip() or "(no description)"
        lines.append(f"{name:<20} {typ:<10} {required:<8} {direction:<10} {pdesc}")
    return "\n".join(lines)


# Instructions:
# Write a new function called `format_operation_details_2` that refactors format_operation_details
# to have similar output, but collects the data from the schema in a more modular way


@dataclass
class _Param:
    name: str
    group: str
    type_: str
    required: str
    description: str


@dataclass
class _Header:
    name: str
    type_: str
    required: str
    direction: str
    description: str


def request_parameters(params: Sequence[dict[str, Any]]) -> Sequence[_Param]:
    param_list: list[_Param] = []
    for param in params:
        if param.get("in") != "header":
            _param = _Param(
                name=param.get("name", ""),
                group=param.get("in", ""),
                type_=param.get("schema", {}).get("type", ""),
                required=str(param.get("required", False)),
                description=(
                    (param.get("schema", {}).get("description", "").strip())
                    or "(no description)"
                )
                + (
                    f" (Possible values: {', '.join(map(str, param['schema']['enum']))})"
                    if "enum" in param.get("schema", {})
                    else ""
                ),
            )

            param_list.append(_param)
    return param_list


def request_headers(params: Sequence[dict[str, Any]]) -> Sequence[_Header]:
    header_list: list[_Header] = []
    for param in params:
        if param.get("in") == "header":
            _header = _Header(
                name=param.get("name", ""),
                type_=param.get("schema", {}).get("type", ""),
                required=str(param.get("required", False)),
                direction="request",
                description=(
                    (param.get("schema", {}).get("description", "").strip())
                    or "(no description)"
                ),
            )
            header_list.append(_header)
    return header_list


def response_headers(headers: dict[str, Any]) -> Sequence[_Header]:
    header_list: list[_Header] = []
    for name, param in headers.items():
        _header = _Header(
            name=name,
            type_=param.get("schema", {}).get("type", ""),
            required=str(param.get("required", False)),
            direction="response",
            description=(
                (param.get("schema", {}).get("description", "").strip())
                or "(no description)"
            ),
        )
        header_list.append(_header)
    return header_list


def response_body_parameters(content_schema: dict[str, Any]) -> Sequence[_Param]:
    param_list: list[_Param] = []
    for name, param in content_schema.get("properties", {}).items():
        _param = _Param(
            name=name,
            group="response",
            type_=param.get("type", ""),
            required=str(param.get("required", False)),
            description=((param.get("description", "").strip()) or "(no description)"),
        )
        param_list.append(_param)
    return param_list


def operation_detail_table(indexed_operation: IndexedOperation) -> Table:
    """Return a Rich Table for one operation, its description, and tables of request parameters, response body parameters, and headers.

    Args:
        indexed_operation (IndexedOperation): The indexed operation object.

    Returns:
        Table: A Rich Table containing the operation details.
    """
    table = Table(show_header=False, header_style="bold magenta")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Operation ID", indexed_operation.operation_id)
    table.add_row(
        "Description", OA.description(indexed_operation) or "(no description)"
    )
    table.add_row("Tags", ", ".join(OA.tags(indexed_operation)))
    table.add_row("Cache Age", str(OA.x_cache_age(indexed_operation) or "Not Defined"))
    table.add_row(
        "Compatibility Date",
        OA.x_compatibility_date(indexed_operation) or "Not Defined",
    )
    table.add_row(
        "Authentication Required", str(OA.is_auth_required(indexed_operation))
    )
    if OA.is_auth_required(indexed_operation):
        scopes = OA.oauth2_scopes(indexed_operation)
        table.add_row("Scopes", ", ".join(scopes))
    return table


def operation_parameters_table(
    indexed_operation: IndexedOperation,
) -> Table:
    """Return a Rich Table for the request parameters of an operation.

    Args:
        indexed_operation (IndexedOperation): The indexed operation object.

    Returns:
        Table: A Rich Table containing the request parameters.
    """
    output_params: list[dict[str, str]] = []
    parameters = OA.request_parameters(indexed_operation)
    for parameter in parameters.values():
        output_param = {
            "Name": parameter.get("name", ""),
            "Group": parameter.get("in", ""),
            "Type": parameter.get("schema", {}).get("type", ""),
            "Required": parameter.get("required", False),
            "Description": parameter.get("description", ""),
        }
        if "enum" in parameter.get("schema", {}):
            output_param["Description"] += (
                f" (Possible values: {', '.join(map(str, parameter['schema']['enum']))})"
            )
        if "default" in parameter.get("schema", {}):
            output_param["Description"] += (
                f" (Default: {parameter['schema']['default']})"
            )
        output_params.append(output_param)
    # todo sort output_params by group, then by name
    output_params.sort(key=lambda x: (x["Group"], x["Name"]))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Group")
    table.add_column("Type")
    table.add_column("Required")
    table.add_column("Description")

    for output_param in output_params:
        table.add_row(
            output_param["Name"],
            output_param["Group"],
            output_param["Type"],
            str(output_param["Required"]),
            output_param["Description"],
        )
    return table


def operation_response_200_panel(
    indexed_operation: IndexedOperation,
) -> Panel:
    """Return a Rich Table for the response body parameters of an operation.

    Args:
        indexed_operation (IndexedOperation): The indexed operation object.
    Returns:
        Table: A Rich Table containing the response body parameters.
    """

    content_schema = OA.response_200_schema(indexed_operation)
    schema_json = JSON.from_data(content_schema, indent=2)
    panel = Panel(schema_json, title="Response Body Schema", expand=False)
    return panel
