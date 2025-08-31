"""Enforce aware datetime for now()."""

from datetime import UTC, datetime


def now_utc() -> datetime:
    """Enforce aware datetime for now()."""
    return datetime.now(UTC)
