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

JWKS_URI = "https://login.eveonline.com/oauth/jwks"
"""The URL to fetch the JSON Web Key Set (JWKS) for validating JWT tokens."""


class TimestampedJwks(TypedDict):
    """The JWKS along with the nanosecond timestamp of when it was fetched."""

    schema: dict[str, Any]
    fetch_timestamp_nano: int


def fetch_jwks(url: str | None = None) -> TimestampedJwks:
    """Fetch the JSON Web Key Set (JWKS) from the JWKS_URI and return it along with a timestamp.

    Returns:
        TimestampedJwks: The JWKS along with the nanosecond timestamp of when it was fetched.
    """
    if url is None:
        url = JWKS_URI
    response = httpx2.get(url)
    response.raise_for_status()
    schema_changelog = response.json()
    fetch_timestamp_nano = Instant.now().timestamp_nanos()
    return TimestampedJwks(
        schema=schema_changelog, fetch_timestamp_nano=fetch_timestamp_nano
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch the JSON Web Key Set (JWKS).")
    parser.add_argument(
        "--jwks-url",
        type=str,
        default=JWKS_URI,
        help="The URL to fetch the JSON Web Key Set (JWKS) from (default: %(default)s)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="The output directory to save the JWKS to. If not provided, will print to stdout.",
    )
    parser.add_argument(
        "--file_name",
        type=str,
        default=None,
        help="The output file name to save the JWKS to. Requires --output-dir to be set. If not provided, will default to 'jwks_{fetch_timestamp_nano}.json'",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="The number of spaces to use for indentation in the JSON output (default: %(default)s)",
    )
    parser.add_argument(
        "--jwks-only",
        action="store_true",
        default=False,
        help="Only output the JWKS without any additional metadata or formatting (default: False)",
    )

    args = parser.parse_args()
    timestamped_jwks = fetch_jwks(args.jwks_url)

    if args.jwks_only:
        output_text = json.dumps(
            timestamped_jwks["schema"], indent=args.indent, sort_keys=True
        )
    else:
        output_text = json.dumps(timestamped_jwks, indent=args.indent, sort_keys=True)

    if args.output_dir:
        fetch_date = Instant.from_timestamp_nanos(
            timestamped_jwks["fetch_timestamp_nano"]
        )
        default_file_name = f"jwks_{fetch_date.to_stdlib().date().isoformat()}_{timestamped_jwks['fetch_timestamp_nano']}.json"
        path_out = (
            Path(args.output_dir) / (args.file_name or default_file_name)
        ).resolve()
        path_out.parent.mkdir(parents=True, exist_ok=True)
        with path_out.open("w") as f:
            f.write(output_text)
        print(f"JWKS saved to: {path_out}")
    else:
        print(output_text, end="")
