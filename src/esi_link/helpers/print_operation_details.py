from typing import Any

from esi_link.esi_schema.eve_openapi_protocol import OperationSchema


def format_operation_details(op_schema: OperationSchema) -> str:
    """
    Return a formatted string for one operation, its description, and tables of request and response parameters.

    Args:
        op_schema (OperationSchema): The operation schema object.

    Returns:
        str: Formatted string with operation details and parameter tables.
    """
    lines: list[str] = []
    lines.append(f"Operation: {op_schema.operation_id}")
    desc = op_schema.schema.get("description", "").strip() or "(no description)"
    lines.append(f"Description: {desc}")
    lines.append("")
    # Request Parameters Table
    lines.append("Request Parameters:")
    lines.append(f"{'Name':<20} {'Group':<10} {'Type':<10} {'Required':<8} Description")
    lines.append("-" * 80)
    # Include all parameters, including those with group 'header'
    for param in op_schema.schema.get("parameters", []):
        name = param.get("name", "")
        group = param.get("in", "")
        typ = param.get("schema", {}).get("type", "")
        required = str(param.get("required", False))
        pdesc = param.get("description", "").strip() or "(no description)"
        lines.append(f"{name:<20} {group:<10} {typ:<10} {required:<8} {pdesc}")
    lines.append("")
    # Response Parameters Table
    lines.append("Response Parameters:")
    lines.append(f"{'Name':<20} {'Group':<10} {'Type':<10} {'Required':<8} Description")
    lines.append("-" * 80)
    response_headers = (
        op_schema.schema.get("responses", {}).get("200", {}).get("headers", {})
    )
    for name, param in response_headers.items():
        group = param.get("in", "header")  # Default to header
        typ = param.get("schema", {}).get("type", "")
        required = str(param.get("required", False))
        pdesc = param.get("description", "").strip() or "(no description)"
        lines.append(f"{name:<20} {group:<10} {typ:<10} {required:<8} {pdesc}")
    return "\n".join(lines)


# Example output for GetMarketsRegionIdHistory (with header request params):
EXAMPLE = """
Operation: GetMarketsRegionIdHistory
Description: Return statistics about a market type in a region

Request Parameters:
Name                 Group      Type       Required  Description
--------------------------------------------------------------------------------
region_id            path       integer    True      Return statistics in this region
type_id              query      integer    True      Return statistics for this type
Accept-Language      header     string     False     The language to use for the response.
X-Compatibility-Date header     string     True      The compatibility date for the request.
If-Modified-Since    header     string     False     The date the resource was last modified. A 304 will be returned if the resource has not been modified since this date.
If-None-Match        header     string     False     The ETag of the previous request. A 304 will be returned if this matches the current ETag.
X-Tenant             header     string     False     The tenant ID for the request.

Response Parameters:
Name                 Group      Type       Required  Description
--------------------------------------------------------------------------------
CacheControl         header     string     False     Directives for caching mechanisms. It controls how the response can be cached, by whom, and for how long.
ContentLanguage      header     string     False     The language used in the response.
ETag                 header     string     False     The ETag value of the response body. Use this with If-None-Match to check whether the resource has changed.
LastModified         header     string     False     The last modified date of the response. Use this with If-Modified-Since to check whether the resource has changed.
"""
