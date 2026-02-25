from typing import Any

from whenever import Instant

from esi_link.v2.helpers.download_file import download_json
from esi_link.v2.models import IndexedEsiSchema
from esi_link.v2.settings import get_settings


def download_schema() -> tuple[dict[str, Any], Instant]:
    """Download the latest ESI schema from the official source.

    Returns:
        A tuple containing the downloaded schema as a dictionary and the timestamp of
        when it was downloaded.
    """
    settings = get_settings()
    url = settings.esi_schema_url
    schema = download_json(url)
    if not validate_schema(schema):
        raise ValueError("Downloaded schema is invalid")
    timestamp = Instant.now()
    return schema, timestamp


def is_local_schema() -> bool:
    """Check if the ESI schema is available locally."""
    settings = get_settings()
    return settings.esi_schema_path.exists()


def load_schema_from_file() -> IndexedEsiSchema:
    """Load the ESI schema from a local file."""
    settings = get_settings()
    schema_path = settings.esi_schema_path
    if not schema_path.exists():
        raise FileNotFoundError(f"ESI schema file not found at {schema_path}")
    schema = schema_path.read_text()
    return IndexedEsiSchema.model_validate_json(schema)


def save_schema_to_file(schema: IndexedEsiSchema) -> None:
    """Save the ESI schema to a local file."""
    settings = get_settings()
    schema_path = settings.esi_schema_path
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    with schema_path.open("w") as f:
        f.write(schema.model_dump_json(indent=2))


def validate_schema(schema: dict[str, Any]) -> bool:
    """Validate the downloaded ESI schema."""
    # Schema is an openapi 3.0 schema, so we can check for the presence of required fields
    required_fields = ["openapi", "info", "paths"]
    for field in required_fields:
        if field not in schema:
            raise ValueError(f"Schema is missing required field: {field}")
    return True
