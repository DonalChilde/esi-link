from typing import Protocol

from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol

from .models import EsiQuery


class ValidationError(Exception):
    """Exception raised for errors in the ESI query validation."""

    pass


class EsiQueryValidatorProtocol(Protocol):
    """Protocol for validating ESI queries."""

    def validate(self, query: EsiQuery) -> None:
        """Validate the given ESI query.

        Args:
            query (EsiQuery): The query to validate.

        RRaises:
            ValidationError: If the query is invalid.
        """
        ...


class SimpleValidator:
    """A simple implementation of the EsiQueryValidatorProtocol that performs basic validation."""

    def __init__(self, eve_api: EsiApiProtocol) -> None:
        self._eve_api = eve_api

    def validate(self, query: EsiQuery) -> None:
        """Validate the given ESI query.

        Args:
            query (EsiQuery): The query to validate.

        Raises:
            ValidationError: If the query is invalid.
        """
        # Add more validation rules as needed
