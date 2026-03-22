"""Generate human readable schema documentation."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yaml import safe_dump

from esi_link.helpers.resolve_json_ref import resolve_internal_refs


@dataclass(slots=True)
class Operation:
    """An OpenAPI operation.

    From an OpenAPI schema, we want to extract the path, method, operation ID, and the full operation schema for each operation defined in the schema. This will allow us to generate human readable documentation for each operation, including the parameters, request body, and authentication requirements.
    """

    path: str
    method: str
    operation_id: str
    schema: dict[str, Any]


def generate_schema_doc(schema: dict[str, Any]) -> str:
    """Generate human readable documentation for an ESI schema.

    Args:
        schema: The ESI schema to generate documentation for.

    Returns:
        A string containing the generated documentation.
    """
    if "openapi" not in schema:
        raise ValueError("Invalid schema: missing 'openapi' field")
    if "info" not in schema:
        raise ValueError("Invalid schema: missing 'info' field")
    if "paths" not in schema:
        raise ValueError("Invalid schema: missing 'paths' field")
    dereferenced_schema = resolve_internal_refs(schema, schema)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate human readable schema documentation."
    )
    parser.add_argument(
        "schema_file",
        type=Path,
        help="The path to the raw schema file to generate documentation for.",
    )
    parser.add_argument(
        "output_directory",
        type=Path,
        help="The path to the output directory to write the generated documentation to.",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Whether to overwrite existing files.",
    )
    args = parser.parse_args()
    with open(args.schema_file) as f:
        schema = json.load(f)
    doc = safe_dump(resolve_internal_refs(schema, schema))
    output_file = args.output_directory / "schema_doc.md"
    if output_file.exists() and not args.overwrite:
        print(
            f"Output file {output_file} already exists and overwrite is not enabled. Skipping generation."
        )
        raise FileExistsError(
            f"Output file {output_file} already exists and overwrite is not enabled."
        )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write(doc)
    print(f"Generated schema documentation written to {output_file}")
