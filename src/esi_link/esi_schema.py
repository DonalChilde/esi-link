"""Functions for working with the ESI schema."""

import json
from pathlib import Path
from typing import Any

from whenever import Instant

from esi_link.helpers.download_file import download_json
from esi_link.helpers.eve_dates import compatibility_date as get_compatibility_date
from esi_link.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.models import IndexedEsiSchema, IndexedSchemaStore, SchemaDownload
from esi_link.settings import EsiLinkSettings


def download_schema(
    settings: EsiLinkSettings, compatibility_date: str | None = None
) -> SchemaDownload:
    """Download the latest ESI schema from the official source.

    Returns:
        A SchemaDownload object containing the downloaded schema and its metadata.
    """
    if compatibility_date is None:
        # Get the current compatibility date for ESI schema downloads.
        compatibility_date = get_compatibility_date()
    params = {"compatibility_date": compatibility_date}
    url = settings.esi_schema_url
    schema = download_json(url, params=params)
    if "error" in schema:
        raise ValueError(f"Error downloading schema: {schema['error']}")
    if not validate_schema(schema):
        # catch other types of invalid schema.
        raise ValueError("Downloaded schema is invalid")
    timestamp = Instant.now()
    return SchemaDownload(
        raw_schema=schema,
        download_date=timestamp,
    )


def save_schemas_to_file(
    raw_schema: dict[str, Any],
    dir_out: Path,
    file_suffix: str,
    file_prefix: str = "esi-schema",
) -> tuple[Path, Path]:
    """Save both the raw, and the dereferenced ESI schema to local files."""
    dir_out.mkdir(parents=True, exist_ok=True)
    raw_schema_path = dir_out / f"{file_prefix}-raw-{file_suffix}.json"
    raw_schema_path.write_text(json.dumps(raw_schema, indent=2))
    dereferenced_schema_path = (
        dir_out / f"{file_prefix}-dereferenced-{file_suffix}.json"
    )
    dereferenced_schema = resolve_internal_refs(raw_schema, raw_schema)
    dereferenced_schema_path.write_text(json.dumps(dereferenced_schema, indent=2))
    return raw_schema_path, dereferenced_schema_path


def load_schema_store(settings: EsiLinkSettings) -> IndexedSchemaStore:
    """Load the ESI schema store from a local file in the app directory."""
    schema_path = settings.schema_store_path
    if not schema_path.exists():
        schema_store = IndexedSchemaStore(schemas={})
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        with schema_path.open("w") as f:
            f.write(schema_store.model_dump_json(indent=2))
        return schema_store
    schema = schema_path.read_text()
    return IndexedSchemaStore.model_validate_json(schema)


def save_schema_store(
    settings: EsiLinkSettings, schema_store: IndexedSchemaStore
) -> None:
    """Save the ESI schema store to a local file in the app directory."""
    schema_path = settings.schema_store_path
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    with schema_path.open("w") as f:
        f.write(schema_store.model_dump_json(indent=2))


def add_schema_to_store(
    settings: EsiLinkSettings, indexed_schema: IndexedEsiSchema
) -> IndexedSchemaStore:
    """Add an indexed ESI schema to the schema store.

    Loads the current schema store, adds the new schema, saves the updated store,
    and returns the updated store.
    """
    schema_store = load_schema_store(settings=settings)
    schema_date = indexed_schema.version
    schema_store.schemas[schema_date] = indexed_schema
    save_schema_store(settings=settings, schema_store=schema_store)
    return schema_store


def validate_schema(raw_schema: dict[str, Any]) -> bool:
    """Validate the downloaded ESI schema."""
    # Schema is an openapi 3.1 schema, so we can check for the presence of required fields
    required_fields = ["openapi", "info", "paths"]
    for field in required_fields:
        if field not in raw_schema:
            raise ValueError(f"Schema is missing required field: {field}")
    return True
