from esi_link.errors import EsiLinkError


class SchemaManagerError(EsiLinkError):
    """Base class for schema manager errors."""

    pass


class SchemaNotFoundError(SchemaManagerError):
    """Raised when a schema is not found in the schema store."""

    pass


class InvalidSchemaError(SchemaManagerError):
    """Raised when a schema is invalid or cannot be processed."""

    pass
