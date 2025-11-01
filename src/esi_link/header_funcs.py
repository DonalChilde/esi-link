"""Functions for retrieving values from ESi headers."""

type HeadersType = tuple[tuple[str, str | None], ...]


def pages_available(headers: HeadersType) -> str:
    """Get the page count from the response headers."""
    for header in headers:
        if header[0].lower() == "x-pages":
            return header[1] or "1"
    return "1"


def last_modified(headers: HeadersType) -> str:
    """Get the last modified timestamp from the response headers."""
    for header in headers:
        if header[0].lower() == "last-modified":
            return header[1] if header[1] else ""
    return ""


def limit_reset(headers: HeadersType) -> str:
    """Get the seconds until the error limit resets from the response headers."""
    for header in headers:
        if header[0].lower() == "x-esi-error-limit-reset":
            return header[1] or ""
    return ""


def limit_remain(headers: HeadersType) -> str:
    """Get the errors remaining from the response headers."""
    default = "100"
    for header in headers:
        if header[0].lower() == "x-esi-error-limit-remain":
            return header[1] or default
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


# FIXME: return strings over ints.


def retry_after(headers: HeadersType) -> str:
    """Get the retry-after seconds from the response headers."""
    for header in headers:
        if header[0].lower() == "retry-after":
            return header[1] if header[1] else ""
    return ""


def rate_limit_group(headers: HeadersType) -> str:
    """Get the rate limit group from the response headers."""
    for header in headers:
        if header[0].lower() == "x-rate-limit-group":
            return header[1] if header[1] else ""
    return ""


def rate_limit_limit(headers: HeadersType) -> str:
    """Get the rate limit from the response headers."""
    default: str = ""
    for header in headers:
        if header[0].lower() == "x-ratelimit-limit":
            return header[1] or default
    return default


def rate_limit_remaining(headers: HeadersType) -> str:
    """Get the rate limit remaining from the response headers."""
    default: str = ""
    for header in headers:
        if header[0].lower() == "x-ratelimit-remaining":
            return header[1] or default
    return default


def rate_limit_used(headers: HeadersType) -> str:
    """Get the rate limit used from the response headers."""
    default: str = ""
    for header in headers:
        if header[0].lower() == "x-ratelimit-used":
            return header[1] or default
    return default
