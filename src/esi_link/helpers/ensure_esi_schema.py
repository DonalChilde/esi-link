"""Ensure that the ESI schema exists at the specified file path."""

from pathlib import Path

from esi_link import USER_AGENT
from esi_link.helpers.download_esi_schema import download_esi_schema
from esi_link.models import EsiSchema


def ensure_esi_schema(
    esi_schema_path: Path,
    esi_schema_url: str,
    force_update: bool = False,
) -> EsiSchema:
    """Ensure that the ESI schema exists at the file path.

    This function checks if the ESI schema file exists at the specified path.
    If it does not exist or if force_update is True, it downloads the schema
    from the provided URL and saves it to the path, returning the new schema.
    If it exists at the path, the schema is loaded and returned.

    Args:
        esi_schema_path: The path to the EsiSchema file.
        esi_schema_url: The URL to download the schema from if it does not exist.
        force_update: If True, force an update of the schema.

    Returns:
        The EsiSchema instance.
    """
    if not esi_schema_path.exists() or force_update:
        # Download the schema from the URL and save it to the path
        esi_schema = download_esi_schema(
            esi_schema_url, headers={"User-Agent": USER_AGENT}
        )
        esi_schema.save_to_file(file_path=esi_schema_path, overwrite=True)
        return esi_schema
    else:
        # Load the schema from the existing file
        esi_schema = EsiSchema.load_from_file(file_path=esi_schema_path)
        return esi_schema
