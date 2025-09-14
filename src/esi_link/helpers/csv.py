"""CSV Utilities.

Check for older version of csv util. Consolidate.
"""

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .validate_file_out import validate_file_out


def write_dicts_to_csv(
    data: Iterable[dict[str, Any]],
    file_path: Path,
    fieldnames: list[str] | None = None,
    overwrite: bool = False,
    **kwargs,
) -> int:
    """write_dicts_to_csv .

    Args:
        data (Iterable[dict[str, Any]]): An Iterable of dicts to write to disk.
        file_path (Path): The file path to write to.
        fieldnames (list[str] | None, optional): Field names to use as column headers. Defaults to None.
        overwrite (bool, optional): Allow overwrititing an existing file. Defaults to False.
        kwargs (): arguments supplied to DictWriter.

    Returns:
        int: The count of records written.
    """
    data_iterator = iter(data)
    count = 0
    try:
        first_item = next(data_iterator)
        count += 1
    except StopIteration:
        return count
    # Determine fieldnames if not provided
    if fieldnames is None:
        fieldnames = list(first_item.keys())
    validate_file_out(file_path=file_path, overwrite=overwrite)
    with open(file_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, **kwargs)
        writer.writeheader()  # Write the header row
        writer.writerow(first_item)
        for row in data_iterator:
            writer.writerow(row)
            count += 1
    return count
