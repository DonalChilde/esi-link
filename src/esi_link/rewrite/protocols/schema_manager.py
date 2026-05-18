# TODO match this with current implementation
from whenever import Instant

from esi_link.rewrite.models.schema import AvailableSchema, EsiSchema, StoredSchema


class SchemaManagerProtocol:
    """Protocol for managing ESI schemas, including storing, retrieving, and adding schemas to the schema store.

    While the Esi schema is versioned by its compatibility date, minor changes do not
    trigger an update of the compatibility date. This means that multiple versions of
    the schema can exist for the same compatibility date.

    To avoid ambiguity when multiple versions of the schema exist for the same compatibility date,
    schemas in the store are indexed by both their compatibility date and their download
    timestamp, to allow for retrieval of specific versions of the schema.
    """

    def get_schema(
        self,
        compatibility_date: str | None,
        at_or_after: int | None,
        exact: bool = False,
    ) -> StoredSchema:
        """Get a schema from the store by compatibility date and timestamp.

        This method retrieves a schema from the store based on the provided compatibility date and timestamp criteria. If multiple schemas match the criteria, the most recent one (based on download timestamp) will be returned.

        Args:
            compatibility_date (str | None): The compatibility date of the schema to retrieve. If None, the latest schema across all compatibility dates will be returned.
            at_or_after (int | None): The timestamp of the schema to retrieve, or None to get the latest schema for the compatibility date.
            exact (bool): If True, only return a schema with the exact timestamp specified in `at_or_after`. If False, return the most recent schema with a timestamp greater than `at_or_after`.

        Returns:
            The StoredSchema that matches the provided criteria.

        Raises:
            SchemaNotFoundError: If no schema matches the provided criteria.
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
