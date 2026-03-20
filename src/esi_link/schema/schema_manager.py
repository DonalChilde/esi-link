"""Schema manager implementation for ESI Link."""

import json
from datetime import date
from pathlib import Path
from typing import Any, TypedDict

from whenever import Instant

from esi_link.helpers.save_text_file import save_text_file
from esi_link.models_and_protocols import (
    IndexedEsiSchema,
    SchemaManagerProtocol,
)
from esi_link.schema.errors import (
    InvalidSchemaError,
    SchemaManagerError,
    SchemaNotFoundError,
)
from esi_link.schema.helpers import from_raw_schema


class StoredSchemaTD(TypedDict):
    download_date: str
    schema: dict[str, Any]


class SchemaManager(SchemaManagerProtocol):
    def __init__(self, schema_directory: Path):
        """File based schema manager.

        The schema files are stored in a directory, with one file per schema.

        The file name is `<compatibility_date>-<timestamp>-schema.json` where compatibility_date
        is the compatibility date of the schema as an iso date string (e.g. "2024-06-01")
        and timestamp is the timestamp of the schema download as an integer (e.g. 1712131200).

        The file content is a JSON object with the following structure:
        ```
        {
            "download_date": "2024-06-01T12:00:00Z",
            "schema": raw_schema_content,
        }
        ```

        Args:
            schema_directory (Path): The directory where schema files are stored.
        """
        self.schema_directory = schema_directory

    def _schema_files(self) -> list[tuple[str, int, Path]]:
        """Return a list of schema files in the schema directory.

        Each item in the list is a tuple containing:
        - compatibility_date (str): The compatibility date of the schema.
        - timestamp (int): The timestamp of the schema download.
        - file_path (Path): The path to the schema file.

        Returns:
            list[tuple[str, int, Path]]: A list of schema files in the schema directory.
        """
        maybe_files = list(self.schema_directory.glob("*-*-schema.json"))
        files: list[tuple[str, int, Path]] = []
        for file in maybe_files:
            try:
                name = file.stem
                parts = name.split("-")
                compatibility_date = "-".join(parts[0:3])
                # Validate the compatibility date format
                _ = date.fromisoformat(compatibility_date)
                if len(parts) < 4:
                    continue
                # Validate that the timestamp part is alphanumeric
                if not parts[3].isalnum():
                    continue
                timestamp = int(parts[3])
                files.append((compatibility_date, timestamp, file))
            except Exception:
                continue
        return files

    def _load_schema_file(self, file_path: Path) -> StoredSchemaTD:
        """Load a schema file and return its content as a StoredSchema.

        Args:
            file_path (Path): The path to the schema file to load.

        Returns:
            StoredSchema: The content of the schema file as a StoredSchema.

        Raises:
            SchemaManagerError: If there is an error loading the schema file.
        """
        try:
            with file_path.open("r") as f:
                content = f.read()
                stored_schema = json.loads(content)
                if not all(key in stored_schema for key in ("download_date", "schema")):
                    raise SchemaManagerError(
                        f"Schema file {file_path} is missing required keys"
                    )
            return stored_schema
        except Exception as e:
            raise SchemaManagerError(
                f"Error loading schema file {file_path}: {str(e)}"
            ) from e

    def _index_a_schema(
        self, stored_schema: StoredSchemaTD, file_path: Path
    ) -> IndexedEsiSchema:
        """Index a raw OpenAPI schema and return an IndexedEsiSchema.

        Args:
            stored_schema (StoredSchema): The stored schema to index.
            file_path (Path): The path to the schema file being indexed.

        Returns:
            IndexedEsiSchema: The indexed schema as an IndexedEsiSchema instance.
        """
        try:
            indexed_schema = from_raw_schema(
                raw_schema=stored_schema["schema"],
                download_date=stored_schema["download_date"],
            )
            return indexed_schema
        except Exception as e:
            raise SchemaManagerError(
                f"Error indexing schema file {file_path}: {str(e)}"
            ) from e

    def get_schema_for_date(
        self, compatibility_date: str, timestamp: int
    ) -> IndexedEsiSchema:
        """Get the ESI schema corresponding to the given compatibility date and timestamp.

        Args:
            compatibility_date (str): The compatibility date of the schema to retrieve.
            timestamp (int): The timestamp of the schema to retrieve.

        Returns:
            IndexedEsiSchema: The ESI schema corresponding to the given compatibility date and timestamp.

        Raises:
            SchemaNotFoundError: If no schema is found for the given compatibility date and timestamp.
            SchemaManagerError: If there is an error loading the schema file.
        """
        available_schemas = self._schema_files()
        for (
            available_compatibility_date,
            available_timestamp,
            file_path,
        ) in available_schemas:
            if (
                available_compatibility_date == compatibility_date
                and available_timestamp == timestamp
            ):
                stored_schema = self._load_schema_file(file_path)
                indexed_schema = self._index_a_schema(stored_schema, file_path)
                return indexed_schema

        raise SchemaNotFoundError(
            f"No schema found for compatibility date {compatibility_date} and timestamp {timestamp}"
        )

    def get_latest_schema(
        self, compatibility_date: str | None = None
    ) -> IndexedEsiSchema:
        """Get the latest ESI schema available in the schema store.

        If compatibility_date is provided, return the latest schema for that compatibility date.
        If compatibility_date is None, return the latest schema across all compatibility dates.

        Args:
            compatibility_date (str | None): The compatibility date to filter schemas by,
                or None to get the latest schema across all compatibility dates.

        Returns:
            IndexedEsiSchema: The latest ESI schema available in the schema store.

        Raises:
            SchemaNotFoundError: If no schemas are found in the schema store.
            SchemaManagerError: If there is an error loading the schema files.
        """
        available_schemas = self._schema_files()
        if not available_schemas:
            raise SchemaNotFoundError("No schemas found in the schema store")
        filtered_schemas = [
            (cd, ts, fp)
            for (cd, ts, fp) in available_schemas
            if compatibility_date is None or cd == compatibility_date
        ]
        if not filtered_schemas:
            raise SchemaNotFoundError(
                f"No schemas found for compatibility date {compatibility_date}"
            )
        latest_schema = max(filtered_schemas, key=lambda x: x[1])
        stored_schema = self._load_schema_file(latest_schema[2])
        indexed_schema = self._index_a_schema(stored_schema, latest_schema[2])
        return indexed_schema

    def available_schemas(self) -> list[tuple[str, int, str]]:
        """Return a list of available compatibility dates for schemas in the store.

        Available schemas are returned as a list of tuples, where each tuple contains:
        - compatibility_date (str): The compatibility date of the schema.
        - timestamp (int): The timestamp of the schema download.
        - datetime (str): The download date and time of the schema as an ISO 8601 string.

        Returns:
            list[tuple[str, int, str]]: A list of available schemas in the store.

        Raises:
            SchemaManagerError: If there is an error loading the schema files.
        """
        available_schemas = self._schema_files()
        schemas_info: list[tuple[str, int, str]] = []
        for compatibility_date, timestamp, file_path in available_schemas:
            try:
                date_time_str = Instant.from_timestamp(timestamp).format_iso()
                schemas_info.append((compatibility_date, timestamp, date_time_str))
            except Exception as e:
                raise SchemaManagerError(
                    f"Error processing schema file {file_path}: {str(e)}"
                ) from e
        # Sort schemas by compatibility date and then by timestamp (newest first)
        schemas_info.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return schemas_info

    def add_schema(self, schema: dict[str, Any], download_date: Instant) -> None:
        """Add a new schema to the schema store.

        This method adds a raw OpenAPI schema to the schema store along with the
        date and time when the schema was downloaded.

        Args:
            schema (dict[str, Any]): The raw OpenAPI schema to add to the store.
            download_date (Instant): The date and time when the schema was downloaded.

        Raises:
            SchemaManagerError: If there is an error saving the schema to the store.
            InvalidSchemaError: If the schema is invalid or cannot be processed.

        """
        # Check the the schema is OpenAPI 3.0 or 3.1
        if "openapi" not in schema or not schema["openapi"].startswith("3."):
            raise InvalidSchemaError("Only OpenAPI 3.0 and 3.1 schemas are supported")
        try:
            version = schema["info"]["version"]
            _ = date.fromisoformat(version)
        except Exception as e:
            raise InvalidSchemaError(
                f"Schema info.version must be a valid ISO date string (e.g. '2024-06-01') - {e}"
            ) from e
        stored_schema = StoredSchemaTD(
            download_date=download_date.format_iso(),
            schema=schema,
        )
        try:
            save_text_file(
                text=json.dumps(stored_schema, indent=2),
                output_dir=self.schema_directory,
                file_name=f"{version}-{download_date.timestamp()}-schema.json",
                overwrite=False,
            )
        except Exception as e:
            raise SchemaManagerError(f"Error saving schema to store: {str(e)}") from e
