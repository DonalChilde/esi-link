"""Protocols for ESI Authentication storage and access."""

from typing import Protocol

import aiohttp

from esi_link.esi_auth.models import (
    CachedMetadata,
    CharacterAuth,
    CharacterToken,
    EveAppCredentials,
    RequestParams,
)


class AuthenticatorProtocol(Protocol):
    """Protocol for authenticating ESI tokens."""

    async def request_character_token(
        self, params: RequestParams, timeout: int = 300
    ) -> CharacterToken:
        """Request a new ESI token.

        Runs the server, gets the token, validates it, and returns the character information.

        This method should be implemented by subclasses to provide the actual logic for requesting a new token.
        """
        ...

    async def refresh_character_token(
        self, token: CharacterToken, client_session: aiohttp.ClientSession
    ) -> CharacterToken:
        """Refresh an existing ESI token.

        Returns a new CharacterToken with updated auth token information.
        """
        ...

    async def revoke_character_token(
        self, token: CharacterToken, client_session: aiohttp.ClientSession
    ) -> None:
        """Revoke an existing ESI token.

        Raises:

        """
        ...

    def prepare_for_request(self, scopes: list[str] | None = None) -> RequestParams:
        """Prepare the authenticator for making requests.

        This method can be used to initialize any necessary state or perform any necessary setup before making requests.
        """
        ...


class CharacterTokenProviderProtocol(Protocol):
    """Protocol for providing ESI tokens."""

    authenticator: AuthenticatorProtocol

    async def get_token(
        self, character_id: int, min_seconds: int = 300
    ) -> CharacterToken:
        """Return the ESI token for the given character ID, optionally refreshing the token if it is about to expire.

        Args:
            character_id: The ID of the character for which to retrieve the token.
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).

        Raises:
            KeyError: If no token for the given character ID exists.
        """
        ...

    async def list_tokens(self, min_seconds: int = 300) -> list[CharacterToken]:
        """Return a list of all ESI tokens, optionally refreshing tokens that are about to expire.

        Args:
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).

        Raises:
            KeyError: If no tokens exist.
        """
        ...


class CharacterTokenManagerProtocol(CharacterTokenProviderProtocol, Protocol):
    """Protocol for managing ESI tokens."""

    def add_token(self, token: CharacterToken) -> None:
        """Add a new ESI token to the provider.

        Raises:
            ValueError: If a token for the same character ID already exists.
        """
        ...

    def remove_token(self, character_id: int) -> None:
        """Remove the ESI token for the given character ID.

        Raises:
            KeyError: If no token for the given character ID exists.
        """
        ...


class AuthProviderProtocol(Protocol):
    """Protocol for providing authentication information."""

    async def character_auth(
        self, character_id: int, min_seconds: int = 300
    ) -> CharacterAuth:
        """Return the authentication information for the given character ID.

        Args:
            character_id: The ID of the character for which to retrieve the authentication information.
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).

        Returns:
            The authentication information for the given character ID.

        Raises:
            KeyError: If no authentication information for the given character ID exists.
        """
        ...

    async def available_characters(self, min_seconds: int = 300) -> list[int]:
        """Return a list of character IDs for which authentication information is available.

        Args:
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).
        """
        ...


class CachedOauthMetadataProviderProtocol(Protocol):
    """Protocol for providing cached OAuth metadata."""

    async def get_cached_metadata(self, max_age: int = 86400) -> CachedMetadata:
        """Return the cached OAuth metadata.

        If the cached metadata is expired, this method requests new metadata and updates the cache.

        Args:
            max_age: The maximum age of the cached metadata, in seconds, before automatic
                update. -1 to disable update of expired metadata. Default is 86400 (1 day).

        Returns:
            The cached OAuth metadata.

        Raises:
            ValueError: If the cached metadata does not exist, and update is disabled.
        """
        ...


class AppCredentialsProviderProtocol(Protocol):
    """Protocol for providing application credentials."""

    # def get_client_id(self) -> str:
    #     """Return the client ID for the application."""
    #     ...

    # def get_scopes(self) -> list[str]:
    #     """Return the list of scopes required for the application."""
    #     ...

    # def get_redirect_uri(self) -> str:
    #     """Return the redirect URI for the application."""
    #     ...

    def add_credentials(self, credentials: EveAppCredentials) -> None:
        """Add the application credentials to the provider."""
        ...

    def remove_credentials(self) -> None:
        """Remove the application credentials from the provider."""
        ...

    def has_credentials(self) -> bool:
        """Return True if the provider has application credentials, False otherwise."""
        ...

    def get_credentials(self) -> EveAppCredentials:
        """Return the application credentials.

        Raises:
            ValueError: If the provider does not have application credentials.
        """
        ...
