"""Tests for Argus request helpers."""

from esi_link.argus.requests import _prepare_post_universe_name_ids


def test_prepare_post_universe_name_ids_filters_unsupported_values() -> None:
    """Large structure IDs should be excluded from PostUniverseNames batches."""
    valid_ids, filtered_ids = _prepare_post_universe_name_ids(
        ids_=[60003760, 1049048886920, 1049311588112, 34]
    )

    assert valid_ids == [60003760, 34]
    assert filtered_ids == [1049048886920, 1049311588112]


def test_prepare_post_universe_name_ids_deduplicates_and_skips_non_positive() -> None:
    """Duplicate and invalid IDs should not be sent to the endpoint."""
    valid_ids, filtered_ids = _prepare_post_universe_name_ids(
        ids_=[0, -1, 30000142, 30000142, 10000002]
    )

    assert valid_ids == [30000142, 10000002]
    assert filtered_ids == []
