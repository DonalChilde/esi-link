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

METADATA_ENDPOINT = "https://login.eveonline.com/.well-known/oauth-authorization-server"
"""The URL to download the ESI auth metadata from."""


class TimestampedMetadata(TypedDict):
    """The ESI auth metadata along with the nanosecond timestamp of when it was fetched."""

    metadata: dict[str, Any]
    fetch_timestamp_nano: int


def fetch_esi_auth_metadata(url: str | None = None) -> TimestampedMetadata:
    """Fetch the ESI auth metadata from the METADATA_ENDPOINT and return it along with a timestamp.

    Returns:
        TimestampedSchema: The ESI schema changelog along with the nanosecond timestamp of when it was fetched.
    """
    if url is None:
        url = METADATA_ENDPOINT
    response = httpx2.get(url)
    response.raise_for_status()
    metadata = response.json()
    fetch_timestamp_nano = Instant.now().timestamp_nanos()
    return TimestampedMetadata(
        metadata=metadata, fetch_timestamp_nano=fetch_timestamp_nano
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch the ESI auth metadata.")
    parser.add_argument(
        "--metadata-url",
        type=str,
        default=METADATA_ENDPOINT,
        help="The URL to fetch the ESI auth metadata from (default: %(default)s)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="The output directory to save the ESI auth metadata to. If not provided, will print to stdout.",
    )
    parser.add_argument(
        "--file_name",
        type=str,
        default=None,
        help="The output file name to save the converted result to. Requires --output-dir to be set. If not provided, will default to 'esi_auth_metadata_{fetch_date}_{fetch_timestamp_nano}.json'",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="The number of spaces to use for indentation in the JSON output (default: %(default)s)",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        default=False,
        help="Only output the metadata without any additional information or formatting (default: False)",
    )

    args = parser.parse_args()
    timestamped_metadata = fetch_esi_auth_metadata(args.metadata_url)

    if args.metadata_only:
        output_text = json.dumps(
            timestamped_metadata["metadata"], indent=args.indent, sort_keys=True
        )
    else:
        output_text = json.dumps(
            timestamped_metadata, indent=args.indent, sort_keys=True
        )

    if args.output_dir:
        fetch_date = Instant.from_timestamp_nanos(
            timestamped_metadata["fetch_timestamp_nano"]
        )
        default_file_name = f"esi_auth_metadata_{fetch_date.to_stdlib().date().isoformat()}_{timestamped_metadata['fetch_timestamp_nano']}.json"
        path_out = (
            Path(args.output_dir) / (args.file_name or default_file_name)
        ).resolve()
        path_out.parent.mkdir(parents=True, exist_ok=True)
        with path_out.open("w") as f:
            f.write(output_text)
        print(f"ESI auth metadata saved to: {path_out}")
    else:
        print(output_text, end="")
