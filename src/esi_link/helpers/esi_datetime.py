"""Helper functions for importing datetime strings from ESI responses."""

from datetime import UTC, datetime


def parse_esi_datetime(data: str) -> datetime:
    """Import a datetime string from eve esi and return iso 8601 format."""
    # Convert the string to a datetime object
    dt = datetime.strptime(data, "%a, %d %b %Y %H:%M:%S %Z")
    dt = dt.astimezone(UTC)
    return dt
