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

ESI_SCHEMA_URL = "https://esi.evetech.net/meta/openapi.json"
"""The URL to download the ESI schema from."""


class TimestampedSchema(TypedDict):
    """The ESI schema along with the nanosecond timestamp of when it was fetched."""

    schema: dict[str, Any]
    fetch_timestamp_nano: int


def _resolve_internal_refs(parent: dict[str, Any], child: Any) -> Any:
    """Recursively resolve internal JSON references ($ref) in a child object.

    Using the provided parent object as the reference root.

    Args:
        parent (dict[str, Any]): The full parent JSON object.
        child (Any): The child subsection to resolve.

    Returns:
        Any: The child object with all internal references resolved.

    Example:
        >>> parent = {
        ...     "components": {
        ...         "schemas": {"A": {"type": "object"}, "B": {"$ref": "#/components/schemas/A"}}
        ...     }
        ... }
        >>> child = parent["components"]["schemas"]["B"]
        >>> _resolve_internal_refs(parent, child)
        {'type': 'object'}
    """

    def _resolve(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"]
                if not ref_path.startswith("#/"):
                    raise ValueError(f"Only internal refs supported, got: {ref_path}")
                # Split and traverse the parent object
                parts = ref_path.lstrip("#/").split("/")
                ref_obj = parent
                for part in parts:
                    ref_obj = ref_obj[part]
                # Recursively resolve the referenced object
                return _resolve(ref_obj)
            else:
                # Recursively resolve all dict values
                return {k: _resolve(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_resolve(item) for item in obj]
        else:
            return obj

    return _resolve(child)


def resolve_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve all internal JSON references ($ref) in the provided schema.

    Args:
        schema (dict[str, Any]): The original JSON schema with potential $ref references.

    Returns:
        dict[str, Any]: The schema with all internal references resolved.
    """
    return _resolve_internal_refs(schema, schema)


def verify_compatibility_date(date_str: str | None) -> str:
    """Verify the provided compatibility date string is in the correct format (YYYY-MM-DD).

    Args:
        date_str (str|None): The compatibility date string to verify.

    Returns:
        str: The verified compatibility date string, or the current date in UTC if None was provided.

    Raises:
        ValueError: If the provided date string is not in the correct format.
    """
    if date_str is not None:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError as e:
            raise ValueError(
                f"Invalid compatibility date format: {date_str}. Expected format: YYYY-MM-DD"
            ) from e
    else:
        return datetime.now(UTC).strftime("%Y-%m-%d")


def fetch_esi_schema(
    url: str | None = None, compatibility_date: str | None = None
) -> TimestampedSchema:
    """Fetch the ESI schema from the specified URL.

    Args:
        url (str | None): The URL to fetch the ESI schema from. Defaults to ESI_SCHEMA_URL.
        compatibility_date (str | None): The compatibility date for the ESI schema. Defaults to current date UTC. If provided, will attempt to fetch the schema from the ESI schema archive for that date (format: YYYY-MM-DD).

    Returns:
        TimestampedSchema: The parsed JSON schema along with the fetch timestamp.
    """
    compatibility_date = verify_compatibility_date(compatibility_date)
    if url is None:
        url = ESI_SCHEMA_URL
    with httpx2.Client() as client:
        response = client.get(url, params={"compatibility_date": compatibility_date})
        response.raise_for_status()
        fetch_timestamp_nano = Instant.now().timestamp_nanos()
        return {"schema": response.json(), "fetch_timestamp_nano": fetch_timestamp_nano}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and resolve the ESI schema.")
    parser.add_argument(
        "--schema-url",
        type=str,
        default=ESI_SCHEMA_URL,
        help="The URL to fetch the ESI schema from (default: %(default)s)",
    )
    parser.add_argument(
        "--compatibility-date",
        type=str,
        default=None,
        help="The compatibility date for the ESI schema. Defaults to current date UTC. If provided, will attempt to fetch the schema from the ESI schema archive for that date (format: YYYY-MM-DD).",
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
        help="Only output the resolved schema without any additional metadata or formatting (default: False)",
    )
    parser.add_argument(
        "--unresolved",
        action="store_true",
        default=False,
        help="Whether to output the raw unresolved schema instead of the resolved schema (default: False)",
    )
    args = parser.parse_args()
    requested_compatibility_date = verify_compatibility_date(args.compatibility_date)
    timestamped_schema = fetch_esi_schema(args.schema_url, requested_compatibility_date)
    reported_compatibility_date = (
        timestamped_schema.get("schema", {}).get("info", {}).get("version", "unknown")
    )
    if args.schema_only:
        if args.unresolved:
            output_text = json.dumps(timestamped_schema["schema"], indent=args.indent)
        else:
            resolved_schema = resolve_schema(timestamped_schema["schema"])
            output_text = json.dumps(resolved_schema, indent=args.indent)
    else:
        if args.unresolved:
            output_text = json.dumps(timestamped_schema, indent=args.indent)
        else:
            resolved_schema = resolve_schema(timestamped_schema["schema"])
            output_data = TimestampedSchema(
                schema=resolved_schema,
                fetch_timestamp_nano=timestamped_schema["fetch_timestamp_nano"],
            )
            output_text = json.dumps(output_data, indent=args.indent)
    if args.output_dir:
        default_file_name = f"esi_schema_{reported_compatibility_date}_{timestamped_schema['fetch_timestamp_nano']}.json"
        path_out = (
            Path(args.output_dir) / (args.file_name or default_file_name)
        ).resolve()
        path_out.parent.mkdir(parents=True, exist_ok=True)
        with path_out.open("w") as f:
            f.write(output_text)
        print(f"ESI schema saved to: {path_out}")
    else:
        print(output_text, end="")
