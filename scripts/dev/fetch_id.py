# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "httpx2>=2.0.0",
#     "whenever>=0.10.0",
# ]
#
# [tool.uv]
# exclude-newer = "7 days"
# ///

# pyright: standard

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

import httpx2
from whenever import Instant

IDS_ENDPOINT = "https://esi.evetech.net/universe/ids"
"""The URL to download the ESI ids from."""


def fetch_esi_ids(names: list[str]) -> dict[str, Any]:
    """Fetch the ESI ids from the endpoint."""
    with httpx2.Client() as client:
        response = client.post(IDS_ENDPOINT, json=names)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ESI ids for given names.")
    parser.add_argument(
        "names",
        nargs="+",
        help="The names to fetch ids for. Names can be of characters, corporations, alliances, factions, etc. Multi-word names should be enclosed in quotes. Example: 'Rixx Javix'",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="The output directory to save the ESI ids to. If not provided, will print to stdout.",
    )
    parser.add_argument(
        "--file_name",
        type=str,
        default=None,
        help="The output file name to save the converted result to. Requires --output-dir to be set. If not provided, will default to 'esi_ids_{fetch_timestamp_nano}.json'",
    )
    args = parser.parse_args()
    ids = fetch_esi_ids(args.names)
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if args.file_name:
            output_file = args.output_dir / args.file_name
        else:
            fetch_timestamp_nano = Instant.now().timestamp_nanos()
            output_file = args.output_dir / f"esi_ids_{fetch_timestamp_nano}.json"
        with output_file.open("w") as f:
            json.dump(ids, f, indent=2)
        print(f"ESI ids saved to {output_file}")
    else:
        print(json.dumps(ids, indent=2))
