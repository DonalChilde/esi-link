"""Tests for cache id utilities."""

from uuid import UUID

from esi_link.helpers.cache_id_from_url import cache_id_from_url


def test_cache_id_from_url_deterministic_order():
    url1 = "https://example.com/foo?b=2&a=1"
    url2 = "https://example.com/foo?a=1&b=2"

    id1 = cache_id_from_url(url1)
    id2 = cache_id_from_url(url2)

    assert isinstance(id1, UUID)
    assert id1 == id2


def test_cache_id_from_url_ignores_fragment_and_normalizes_host():
    url_with_fragment = "HTTP://Example.com/foo?x=1#section"
    url_normalized = "http://example.com/foo?x=1"

    id1 = cache_id_from_url(url_with_fragment)
    id2 = cache_id_from_url(url_normalized)

    assert id1 == id2
