"""Generate human readable schema documentation."""

import json
from pathlib import Path
from typing import Any

from whenever import Instant
from yaml import safe_dump

from esi_link.models_and_protocols import EsiSchema, SchemaOperation


def _operation_variation_1(operation: SchemaOperation) -> str:
    """Generate human readable documentation for an ESI schema operation with variation 1.

    This variation includes the path, method, description, parameters, request body, and authentication requirements.

    Args:
        operation: The ESI schema operation to generate documentation for.

    Returns:
        A string containing the generated documentation.
    """
    return f"""- `{operation.operation_id}`  
**Operation ID**: `{operation.operation_id}`  
**Path**: `{operation.path}`  
**Method**: `{operation.method}`  
**Description**: {operation.description.replace("\n", " ")}  
**Authentication**: {operation.auth_required}  
**Tags**: {", ".join(operation.tags) if operation.tags else "None"}  
**Parameters**:  
```json
{json.dumps(operation.path_and_query_parameters, indent=2)}
```
**Request Body**:
```json
{json.dumps(operation.request_body, indent=2)}
```
**Response**:  
```json
{json.dumps(operation.responses, indent=2)}
```
"""


def generate_operation_doc(operation: SchemaOperation) -> str:
    """Generate human readable documentation for an ESI schema operation.

    Args:
        operation: The ESI schema operation to generate documentation for.

    Returns:
        A string containing the generated documentation.
    """
    return _operation_variation_1(operation)


def generate_esi_schema_doc(schema: EsiSchema, download_date: Instant | None) -> str:
    """Generate human readable documentation for an ESI schema.

    Args:
        schema: The ESI schema to generate documentation for.
        download_date: The date the schema was downloaded, if available.

    Returns:
        A string containing the generated documentation.
    """
    operation_id_by_tag = schema.operation_id_by_tag
    doc = f"""# ESI Schema Documentation
**Download Date**: {download_date.format_iso() if download_date else "Unknown"}
## Operations
"""
    for tag, operation_ids in operation_id_by_tag.items():
        doc += f"### {tag}\n\n"
        for operation_id in operation_ids:
            operation = schema.operations[operation_id]
            doc += generate_operation_doc(operation) + "\n\n"
    return doc


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
    esi_schema = EsiSchema.from_raw_schema(schema)
    doc = generate_esi_schema_doc(esi_schema, download_date=Instant.now())
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
