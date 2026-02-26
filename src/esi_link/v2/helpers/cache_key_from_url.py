"""Functions for generating cache keys from URLs."""

from uuid import NAMESPACE_URL, UUID, uuid5

from esi_link.v2.helpers.canonicalize_url import canonicalize_url

ESI_LINK_NAMESPACE = uuid5(NAMESPACE_URL, "esi-link")


def cache_key_from_url(url: str) -> UUID:
    """Generate a cache key UUID from a URL."""
    canonical_url = canonicalize_url(url)
    return uuid5(ESI_LINK_NAMESPACE, canonical_url)
