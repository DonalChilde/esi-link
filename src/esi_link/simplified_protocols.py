from whenever import Instant

from esi_link.simplified_models import AvailableSchema, EsiSchema, StoredSchema


class SchemaManagerProtocol:
    """Protocol for managing ESI schemas, including storing, retrieving, and adding schemas to the schema store.

    While the Esi schema is versioned by its compatibility date, minor changes do not
    trigger an update of the compatibility date. This means that multiple versions of
    the schema can exist for the same compatibility date.

    To avoid ambiguity when multiple versions of the schema exist for the same compatibility date,
    schemas in the store are indexed by both their compatibility date and their download
    timestamp, to allow for retrieval of specific versions of the schema.
    """

    def get_schema_for_date(
        self, compatibility_date: str, timestamp: int
    ) -> StoredSchema:
        """Get the ESI schema corresponding to the given compatibility date and timestamp.

        Args:
            compatibility_date (str): The compatibility date of the schema to retrieve.
            timestamp (int): The timestamp of the schema to retrieve.

        Returns:
            StoredSchema: The ESI schema corresponding to the given compatibility date and timestamp.

        Raises:
            SchemaNotFoundError: If no schema is found for the given compatibility date and timestamp.
            SchemaManagerError: If there is an error loading the schema file.
        """
        ...

    def get_latest_schema(self, compatibility_date: str | None) -> StoredSchema:
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
        ...

    def available_schemas(self) -> list[AvailableSchema]:
        """Return a list of available compatibility dates for schemas in the store.

        Available schemas are returned as a list of AvaliableSchema, where each instance contains:
        - compatibility_date (str): The compatibility date of the schema.
        - timestamp (int): The timestamp of the schema download.
        - datetime (str): The download date and time of the schema as an ISO 8601 string.

        Returns:
            list[AvailableSchema]: A list of available schemas in the store, sorted by
                compatibility date and then by timestamp (newest first).

        Raises:
            SchemaManagerError: If there is an error loading the schema files.
        """
        ...

    def add_schema(self, schema: EsiSchema, download_date: Instant) -> None:
        """Add a new schema to the schema store.

        This method adds a raw OpenAPI schema to the schema store along with the
        date and time when the schema was downloaded.

        Args:
            schema (EsiSchema): The EsiSchema to add to the store.
            download_date (Instant): The date and time when the schema was downloaded.

        Raises:
            SchemaManagerError: If there is an error saving the schema to the store.
            InvalidSchemaError: If the schema is invalid or cannot be processed.

        """
        ...
