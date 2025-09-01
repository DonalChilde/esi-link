from esi_link.esi_schema.eve_openapi_protocol import OperationSchema


def format_operation_details(op_schema: OperationSchema) -> str:
    """
    Return a formatted string for one operation, its description, and tables of request parameters, response body parameters, and headers.

    Args:
        op_schema (OperationSchema): The operation schema object.

    Returns:
        str: Formatted string with operation details and parameter tables.
    """
    lines: list[str] = []
    lines.append(f"Operation: {op_schema.operation_id}")
    tag_group = op_schema.schema.get("tags", [])
    lines.append(f"Tags: {', '.join(tag_group)}")
    desc = op_schema.schema.get("description", "").strip() or "(no description)"
    lines.append(f"Description: {desc}")
    cache_age = op_schema.schema.get("x-cache-age", "Not Defined")
    lines.append(f"Cache Age: {cache_age}")
    compatibility_date = op_schema.schema.get("x-compatibility-date", "Not Defined")
    lines.append(f"Compatibility Date: {compatibility_date}")
    # Authorization Required field
    security = op_schema.schema.get("security")
    lines.append("Authorization Required:")
    if security and isinstance(security, list):
        found = False
        for entry in security:
            if "OAuth2" in entry:
                scopes = entry["OAuth2"]
                if scopes:
                    for scope in scopes:
                        lines.append(f"  - {scope}")
                    found = True
        if not found:
            lines.append("  - public")
    else:
        lines.append("  - public")
    lines.append("")
    # Request Parameters Table (excluding headers)
    lines.append("Request Parameters:")
    lines.append(f"{'Name':<20} {'Group':<10} {'Type':<10} {'Required':<8} Description")
    lines.append("-" * 80)
    for param in op_schema.schema.get("parameters", []):
        if param.get("in") != "header":
            name = param.get("name", "")
            group = param.get("in", "")
            typ = param.get("schema", {}).get("type", "")
            required = str(param.get("required", False))
            pdesc = (
                param.get("schema", {}).get("description", "").strip()
                or "(no description)"
            )
            if "enum" in param.get("schema", {}):
                enum_vals = param["schema"]["enum"]
                pdesc += f" (Possible values: {', '.join(map(str, enum_vals))})"
            lines.append(f"{name:<20} {group:<10} {typ:<10} {required:<8} {pdesc}")
    lines.append("")
    # Response Body Parameters Table
    content_schema = (
        op_schema.schema.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    container_type = content_schema.get("type", "Unknown")
    content_type = content_schema.get("items", {}).get("type", "Unknown")
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
    for param in op_schema.schema.get("parameters", []):
        if param.get("in") == "header":
            name = param.get("name", "")
            typ = param.get("schema", {}).get("type", "")
            required = str(param.get("required", False))
            direction = "request"
            pdesc = param.get("description", "").strip() or "(no description)"
            lines.append(f"{name:<20} {typ:<10} {required:<8} {direction:<10} {pdesc}")
    # Response headers
    response_headers = (
        op_schema.schema.get("responses", {}).get("200", {}).get("headers", {})
    )
    for name, param in response_headers.items():
        typ = param.get("schema", {}).get("type", "")
        required = str(param.get("required", False))
        direction = "response"
        pdesc = param.get("description", "").strip() or "(no description)"
        lines.append(f"{name:<20} {typ:<10} {required:<8} {direction:<10} {pdesc}")
    return "\n".join(lines)


# Example output for GetMarketsRegionIdHistory (with array container):
EXAMPLE = """
Operation: GetMarketsRegionIdHistory
Description: Return statistics about a market type in a region
Authorization Required: True

Request Parameters:
Name                 Group      Type       Required  Description
--------------------------------------------------------------------------------
region_id            path       integer    True      Return statistics in this region
type_id              query      integer    True      Return statistics for this type

Response Body Parameters (container: array):
Name                 Group      Type       Required  Description
--------------------------------------------------------------------------------
(date_founded)       body[item] string     True      (no description)

Headers:
Name                 Type       Required  Direction  Description
--------------------------------------------------------------------------------
Accept-Language      string     False     request    The language to use for the response.
X-Compatibility-Date string     True      request    The compatibility date for the request.
If-Modified-Since    string     False     request    The date the resource was last modified. A 304 will be returned if the resource has not been modified since this date.
If-None-Match        string     False     request    The ETag of the previous request. A 304 will be returned if this matches the current ETag.
X-Tenant             string     False     request    The tenant ID for the request.
CacheControl         string     False     response   Directives for caching mechanisms. It controls how the response can be cached, by whom, and for how long.
ContentLanguage      string     False     response   The language used in the response.
ETag                 string     False     response   The ETag value of the response body. Use this with If-None-Match to check whether the resource has changed.
LastModified         string     False     response   The last modified date of the response. Use this with If-Modified-Since to check whether the resource has changed.
"""
