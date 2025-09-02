"""SchemaStore module for managing the ESI OpenAPI schema.

This module provides the SchemaStore class, which supports downloading, saving, and loading
the Eve Online ESI OpenAPI schema. It ensures schema validity and tracks metadata such as
download date and schema UUID.

Classes:
    SchemaStoreData: Pydantic model for schema metadata and content.
    SchemaStore: Main class for schema management.

Typical usage example:
    store = SchemaStore(file_path=Path('schema.json'))
    schema = store.esi_schema
    store.update()
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from esi_link.helpers.resolve_json_ref import resolve_internal_refs

from ..helpers.download_file import download_text
from ..helpers.now_utc import now_utc

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# TODO move schema de-reference to schema store.


class SchemaStoreData(BaseModel):
    """Pydantic model for storing ESI schema metadata and content.

    Attributes:
        id_ (UUID): Unique identifier for the schema.
        download_date (str): ISO 8601 UTC download date.
        esi_schema (dict[str, Any]): The ESI OpenAPI schema as a dictionary.
    """

    id_: UUID
    download_date: str
    esi_schema: dict[str, Any]


class SchemaStore:
    """Manages the ESI OpenAPI schema: download, save, load, and update.

    When initialized with a file path, the schema is loaded from the file. Note that the
    file must exist. To create a new schema store, use the class method
    SchemaStore.from_download() instead. If no file path is provided, the schema also
    cannot be saved. This only occurs when the instance is created without a file path
    from the class method SchemaStore.from_download.

    Attributes:
        _store_path (Path | None): Path to store file, if used.
        _schema_url (str): URL to download schema from.
        _store_data (SchemaStoreData | None): Loaded schema data and metadata.

    Raises:
        ValueError: On invalid schema, missing file, or failed operations.
    """

    def __init__(
        self,
        store_path: Path | None,
        *,
        indent_on_save: int = 2,
        schema_url: str = "https://esi.evetech.net/meta/openapi.json",
    ) -> None:
        """Initialize SchemaStore, loading from file or downloading schema.

        Args:
            store_path (Path | None): Path to schema file, or None to download.
            schema_url (str): URL to download schema from.

        Raises:
            ValueError: If store_path is invalid or schema is invalid.
        """
        self._store_path = store_path
        self._schema_url = schema_url
        self._store_data: SchemaStoreData | None = None
        self._indent_on_save = indent_on_save

        if self._store_path is not None:
            self._store_data = self._load_store_data()

    @classmethod
    def from_download(
        cls,
        *,
        store_path: Path | None,
        schema_url: str = "https://esi.evetech.net/meta/openapi.json",
        indent_on_save: int = 2,
    ) -> "SchemaStore":
        """Create a SchemaStore instance by downloading the schema.

        Args:
            store_path (Path | None): Path to store file, or None to not save.
            schema_url (str): URL to download schema from.
            indent_on_save (int): Indentation level for saving JSON.

        Returns:
            SchemaStore: A new SchemaStore instance.
        """
        instance = cls(
            store_path=None, schema_url=schema_url, indent_on_save=indent_on_save
        )
        instance._update_store()
        instance._store_path = store_path
        if store_path:
            instance._save_store_data()
        return instance

    @classmethod
    def from_schema_file(
        cls,
        *,
        schema_path: Path,
        download_date: str,
        store_path: Path | None,
        indent_on_save: int = 2,
    ) -> "SchemaStore":
        """Create a SchemaStore instance by loading the schema from a file.

        If <store_path> is provided, the schema will be saved to that path, but
        will not overwrite any existing files.

        Args:
            schema_path (Path): Path to the schema file.
            download_date (str): ISO 8601 UTC download date.
            store_path (Path | None): Path to the store file, or None to not save.

        Returns:
            SchemaStore: A new SchemaStore instance.
        """
        schema_text = schema_path.read_text()
        schema_json = json.loads(schema_text)
        resolved_schema = resolve_internal_refs(parent=schema_json, child=schema_json)
        download_date_resolved = datetime.fromisoformat(download_date).astimezone(UTC)
        if "openapi" not in schema_json:
            raise ValueError("Invalid ESI schema: 'openapi' key not found.")
        store_data = SchemaStoreData(
            id_=uuid4(),
            download_date=download_date_resolved.isoformat(),
            esi_schema=resolved_schema,
        )
        instance = cls(None, indent_on_save=indent_on_save)
        instance._store_data = store_data
        instance._store_path = store_path
        if store_path:
            instance._save_store_data()
        return instance

    @classmethod
    def from_obj(
        cls,
        *,
        obj: dict[str, Any],
        download_date: str,
        store_path: Path | None,
        indent_on_save: int = 2,
    ) -> "SchemaStore":
        """Create a SchemaStore instance from a dictionary object.

        Args:
            obj (dict[str, Any]): The dictionary object containing schema data.
            download_date (str): ISO 8601 UTC download date.
            store_path (Path | None): Path to the store file, or None to not save.

        Returns:
            SchemaStore: A new SchemaStore instance.
        """
        if "openapi" not in obj:
            raise ValueError("Invalid ESI schema: 'openapi' key not found.")
        download_date_resolved = datetime.fromisoformat(download_date).astimezone(UTC)
        instance = cls(None, indent_on_save=indent_on_save)
        resolved_schema = resolve_internal_refs(parent=obj, child=obj)
        instance._store_data = SchemaStoreData(
            id_=uuid4(),
            download_date=download_date_resolved.isoformat(),
            esi_schema=resolved_schema,
        )
        instance._store_path = store_path
        if store_path:
            instance._save_store_data()
        return instance

    def update(self, save_to_file: bool = True) -> None:
        """Download schema and update the store, optionally saving to file.

        Args:
            save_to_file (bool): Whether to save schema to file after update.

        Raises:
            ValueError: If schema download fails.
        """
        self._update_store()
        if save_to_file:
            self._save_store_data()

    def _load_store_data(self) -> SchemaStoreData:
        """Load store data from file and validate its contents.

        Returns:
            SchemaStoreData: Loaded schema data and metadata.

        Raises:
            ValueError: If file is missing, invalid, or schema is invalid.
        """
        if self._store_path is None:
            raise ValueError("SchemaStore file_path is not set.")
        if not self._store_path.is_file():
            raise ValueError(f"SchemaStore file not found at: {self._store_path}")
        try:
            text_input = self._store_path.read_text()
            result = SchemaStoreData.model_validate_json(text_input)
            if "openapi" not in result.esi_schema:
                raise ValueError("Invalid ESI schema: 'openapi' key not found.")
        except Exception as e:
            raise ValueError(f"Failed to load ESI schema: {e}") from e
        return result

    def _save_store_data(self) -> None:
        """Save the store data to file.

        Raises:
            ValueError: If schema is not loaded or file path is not set
        """
        if self._store_data is None:
            raise ValueError("ESI schema is not loaded. Nothing to save.")
        if self._store_path is None:
            raise ValueError("SchemaStore file_path is not set.")
        if not self._store_path.parent.exists():
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_path.write_text(
            self._store_data.model_dump_json(indent=self._indent_on_save)
        )

    def _download_schema(self, url: str) -> dict[str, Any]:
        """Download a fresh copy of the ESI openapi schema.

        Args:
            url (str): URL to download schema from.

        Returns:
            dict[str, Any]: The downloaded schema as a dictionary.

        Raises:
            ValueError: If schema is invalid or missing 'openapi' key.
        """
        text = download_text(url)
        schema = json.loads(text)
        resolved_schema = resolve_internal_refs(parent=schema, child=schema)
        if "openapi" not in resolved_schema:
            raise ValueError("Invalid ESI schema: 'openapi' key not found.")
        return resolved_schema

    def _update_store(self) -> None:
        """Download the ESI OpenAPI schema and update the store.

        Raises:
            Exception: If schema download fails.
        """
        try:
            schema = self._download_schema(self._schema_url)
        except Exception as e:
            logger.error(f"Failed to update schema: {e}")
            raise e
        self._store_data = SchemaStoreData(
            id_=uuid4(), download_date=now_utc().isoformat(), esi_schema=schema
        )

    @property
    def esi_schema(self) -> dict[str, Any]:
        """Return the loaded ESI schema as a dictionary.

        Returns:
            dict[str, Any]: The ESI OpenAPI schema.

        Raises:
            ValueError: If schema is not loaded.
        """
        if self._store_data is None:
            raise ValueError("ESI schema is not loaded.")
        return self._store_data.esi_schema

    @property
    def schema_id(self) -> UUID:
        """Return the UUID of the loaded ESI schema.

        Returns:
            UUID: The unique identifier for the schema.

        Raises:
            ValueError: If schema is not loaded.
        """
        if self._store_data is None:
            raise ValueError("ESI schema is not loaded.")
        return self._store_data.id_

    @property
    def download_date(self) -> str:
        """Return the download date of the loaded ESI schema.

        Returns:
            str: The ISO 8601 UTC download datetime.

        Raises:
            ValueError: If schema is not loaded.
        """
        if self._store_data is None:
            raise ValueError("ESI schema is not loaded.")
        return self._store_data.download_date
