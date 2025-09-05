"""Functions for retrieving values from ESi headers."""

HeadersType = tuple[tuple[str, str | None], ...]


def page_count(headers: HeadersType) -> int:
    """Get the page count from the response headers."""
    for header in headers:
        if header[0].lower() == "x-pages":
            return int(header[1] or 1)
    return 1


def last_modified(headers: HeadersType) -> str:
    """Get the last modified timestamp from the response headers."""
    for header in headers:
        if header[0].lower() == "last-modified":
            return header[1] if header[1] else ""
    return ""


def limit_reset(headers: HeadersType) -> int:
    """Get the seconds until the error limit resets from the response headers."""
    default: int = -1
    for header in headers:
        if header[0].lower() == "x-esi-error-limit-reset":
            return int(header[1] or default)
    return default


def limit_remain(headers: HeadersType) -> int:
    """Get the errors remaining from the response headers."""
    default: int = 100
    for header in headers:
        if header[0].lower() == "x-esi-error-limit-remain":
            return int(header[1] or default)
    return default


def expires(headers: HeadersType) -> str:
    """Get the expires timestamp from the response headers."""
    for header in headers:
        if header[0].lower() == "expires":
            return header[1] if header[1] else ""
    return ""


def etag(headers: HeadersType) -> str:
    """Get the ETag from the response headers."""
    for header in headers:
        if header[0].lower() == "etag":
            return header[1] if header[1] else ""
    return ""


def inject_compatibility_date(headers: dict[str, str], compatibility_date: str) -> None:
    """Inject the compatibility date into the request headers."""
    headers["X-Esi-Compatibility-Date"] = compatibility_date
