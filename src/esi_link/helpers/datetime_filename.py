"""Make datetime strings safe for use in filenames."""

from datetime import datetime


def file_safe_datetime_string(dt: datetime) -> str:
    """Convert a datetime object to a string suitable for use in filenames.

    Example:
        2025-07-17T14_54_23_222827P00_00

    Args:
        dt (datetime): The datetime object to convert.

    Returns:
        str: A modified ISO8601 string with [:.] replaced by _ and [+] replaced by P.
    """
    iso_string = dt.isoformat()
    safe_string = file_safe_iso_datetime_string(iso_string)
    return safe_string


def file_safe_iso_datetime_string(iso_string: str) -> str:
    """Convert an ISO8601 datetime string to a string suitable for use in filenames.

    Example:
        2025-07-17T14_54_23_222827P00_00

    Args:
        iso_string (str): The ISO8601 datetime string to convert.

    Returns:
        str: A modified ISO8601 string with [:.] replaced by _ and [+] replaced by P.
    """
    safe_string = iso_string.replace(":", "_").replace(".", "_").replace("+", "P")
    return safe_string
