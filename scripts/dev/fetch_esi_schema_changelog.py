# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "httpx2>=2.0.0",
#     "whenever>=0.10.0",
# ]
# ///


import argparse
import json
from pathlib import Path
from typing import Any, TypedDict

import httpx2
from whenever import Instant

ESI_SCHEMA_CHANGELOG_URL = "https://esi.evetech.net/meta/changelog"
"""The URL to download the ESI schema changelog from."""


class TimestampedSchemaChangelog(TypedDict):
    """The ESI schema changelog along with the nanosecond timestamp of when it was fetched."""

    schema: dict[str, Any]
    fetch_timestamp_nano: int


def fetch_esi_schema_changelog(url: str | None = None) -> TimestampedSchemaChangelog:
    """Fetch the ESI schema changelog from the ESI_SCHEMA_CHANGELOG_URL and return it along with a timestamp.

    Returns:
        TimestampedSchemaChangelog: The ESI schema changelog along with the nanosecond timestamp of when it was fetched.
    """
    if url is None:
        url = ESI_SCHEMA_CHANGELOG_URL
    response = httpx2.get(url)
    response.raise_for_status()
    schema_changelog = response.json()
    fetch_timestamp_nano = Instant.now().timestamp_nanos()
    return TimestampedSchemaChangelog(
        schema=schema_changelog, fetch_timestamp_nano=fetch_timestamp_nano
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch the ESI schema changelog.")
    parser.add_argument(
        "--schema-url",
        type=str,
        default=ESI_SCHEMA_CHANGELOG_URL,
        help="The URL to fetch the ESI schema changelog from (default: %(default)s)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="The output directory to save the ESI schema to. If not provided, will print to stdout.",
    )
    parser.add_argument(
        "--file_name",
        type=str,
        default=None,
        help="The output file name to save the converted result to. Requires --output-dir to be set. If not provided, will default to 'esi_schema_{compatibility_date}_{fetch_timestamp_nano}.json'",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="The number of spaces to use for indentation in the YAML output (default: %(default)s)",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        default=False,
        help="Only output the schema changelog without any additional metadata or formatting (default: False)",
    )

    args = parser.parse_args()
    timestamped_schema = fetch_esi_schema_changelog(args.schema_url)

    if args.schema_only:
        output_text = json.dumps(
            timestamped_schema["schema"], indent=args.indent, sort_keys=True
        )
    else:
        output_text = json.dumps(timestamped_schema, indent=args.indent, sort_keys=True)

    if args.output_dir:
        fetch_date = Instant.from_timestamp_nanos(
            timestamped_schema["fetch_timestamp_nano"]
        )
        default_file_name = f"esi_schema_changelog_{fetch_date.to_stdlib().date().isoformat()}_{timestamped_schema['fetch_timestamp_nano']}.json"
        path_out = (
            Path(args.output_dir) / (args.file_name or default_file_name)
        ).resolve()
        path_out.parent.mkdir(parents=True, exist_ok=True)
        with path_out.open("w") as f:
            f.write(output_text)
        print(f"ESI schema changelog saved to: {path_out}")
    else:
        print(output_text, end="")
