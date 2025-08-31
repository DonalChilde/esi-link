"""Utilities for generating cache identifiers.

This module provides a function to generate a deterministic UUID based on a URL.
The URL is canonicalized to ensure the same cache id regardless of the order of
query parameters or case differences in scheme/host.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, UUID, uuid5


def _canonicalize_url(url: str) -> str:
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


def cache_id_from_url(url: str) -> UUID:
    """Generate a UUIDv5 from a URL string for use as a cache id.

    The URL is canonicalized so that logically equivalent URLs (e.g., differing
    only in query parameter order) yield the same UUID.
    """
    canonical = _canonicalize_url(url)
    return uuid5(NAMESPACE_URL, canonical)
