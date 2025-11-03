"""Functions to canonicalize URLs for stable hashing."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def canonicalize_url(url: str) -> str:
    """Return a canonical form of the URL suitable for stable hashing.

    Normalizations applied:
    - Lowercase scheme and host.
    - Sort query parameters by key (then value) and re-encode.
    - Drop URL fragment.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path or ""

    # Preserve multiple values and blank values; sort by key then value
    query_pairs: list[tuple[str, str]] = parse_qsl(parts.query, keep_blank_values=True)
    query_pairs.sort(key=lambda kv: (kv[0], kv[1]))
    query = urlencode(query_pairs, doseq=True)

    # Drop fragment to avoid treating anchors as separate cacheable resources
    fragment = ""

    return urlunsplit((scheme, netloc, path, query, fragment))
