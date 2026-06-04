"""ESI date helpers."""

from whenever import Instant


def latest_schema_date() -> str:
    """Get the latest possible schema date as a string in the format YYYY-MM-DD.

    EVE Esi schemas update at downtime, which is currently at 11:00 UTC. Since it is not
    possible to get a schema with a future compatibility date, we can use the previous EVE
    day as the latest possible schema date.

    Returns:
        Latest possible schema date as a string in the format YYYY-MM-DD.
    """
    yesterday = Instant.now().subtract(hours=11)
    return yesterday.format("YYYY-MM-DD")
