"""Functions for working with eve time."""

from whenever import Instant, TimeDelta


def eve_time() -> Instant:
    """Get the current time in EVE Online's timezone (UTC)."""
    return Instant.now()


def current_compatibility_date() -> str:
    """Get the current compatibility date for ESI schema download requests.

    The compatibility date updates at downtime, which is every day at 11:00 UTC.
    Before downtime, use yesterdays date (UTC) as the compatibility date, after downtime
    use todays date (UTC) as the compatibility date. The latest Compatibility date is used
    to get the latest ESI Schema, which is versioned to that date.

    Returns:
        The current compatibility date as an ISO formatted string (YYYY-MM-DD).
    """
    now = eve_time()
    next_dt = next_downtime()
    till_dt = next_dt - now
    if till_dt <= TimeDelta(hours=11):
        # If we're within 11 hours of the next downtime, use the previous day as the compatibility date
        return now.subtract(hours=24).py_datetime().date().isoformat()
    else:
        return now.py_datetime().date().isoformat()


def next_downtime() -> Instant:
    """Calculate the next EVE Online downtime as an Instant.

    EVE Online has a scheduled downtime every day at 11:00 UTC. This function calculates
    the next downtime as an Instant in UTC.
    """
    now = eve_time()
    now_dt = now.py_datetime()
    today_downtime = Instant.from_utc(
        year=now_dt.year,
        month=now_dt.month,
        day=now_dt.day,
        hour=11,
    )
    if now >= today_downtime:
        # If it's already past today's downtime, calculate for tomorrow's downtime
        tomorrow_downtime = today_downtime.add(hours=24)
        return tomorrow_downtime
    else:
        return today_downtime


def till_downtime() -> TimeDelta:
    """Calculate the time until the next EVE Online downtime.

    EVE Online has a scheduled downtime every day at 11:00 UTC. This function calculates
    the time remaining until the next downtime.
    """
    now = eve_time()
    next_downtime_instant = next_downtime()
    return next_downtime_instant - now
