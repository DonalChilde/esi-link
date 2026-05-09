"""AuthStore for managing ESI authentication tokens on disk."""

from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Annotated, Self

import aiohttp
from annotated_types import Ge, Le
from pydantic import RootModel

from esi_link.esi_auth.models import CharacterToken, EsiAppCredentials
from esi_link.esi_auth.token_tool import TokenTool


@dataclass(slots=True, frozen=True)
class AuthStore:
    """Data model for ESI auth data."""

    app_credentials: EsiAppCredentials
    character_tokens: dict[int, CharacterToken] = field(
        default_factory=dict[int, CharacterToken]
    )


AuthStoreRoot = RootModel[AuthStore]


class AuthStoreDisk:
    def __init__(
        self,
        auth_store_path: Path,
        token_tool: TokenTool,
    ):
        """Context manager for loading and saving the ESI auth store from disk.

        Args:
            auth_store_path: The file path to the auth store JSON file on disk.
            token_tool: The TokenTool instance to use for refreshing tokens.
        """
        self.auth_store_path = auth_store_path
        self.token_tool = token_tool
        self._auth_store: AuthStore | None = None
        self._auth_store_dirty: bool = False

    async def __aenter__(self) -> Self:
        """Load the auth store from disk, or initialize an empty cache if the file doesn't exist."""
        if self._auth_store is not None:
            raise RuntimeError("AuthStoreDisk context manager already entered.")
        if self.auth_store_path.exists():
            if not self.auth_store_path.is_file():
                raise RuntimeError(
                    f"Auth store path {self.auth_store_path} is not a file."
                )
            self._auth_store = AuthStoreRoot.model_validate_json(
                self.auth_store_path.read_text()
            ).root
        else:
            raise ValueError(f"Auth store file {self.auth_store_path} does not exist.")
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Save the auth store to disk if it was modified during the context."""
        if self._auth_store is None:
            raise RuntimeError("AuthStoreDisk context manager not entered.")
        if not self._auth_store_dirty:
            self._auth_store = None
            return
        data_root = AuthStoreRoot(root=self._auth_store)
        self.auth_store_path.write_text(data_root.model_dump_json(indent=2))
        self._auth_store = None

    async def _refresh_character_token(
        self, character_token: CharacterToken, session: aiohttp.ClientSession
    ) -> CharacterToken:

        refreshed_oauth_token = await self.token_tool.refresh_token(
            client_id=self._auth_store.app_credentials.clientId,  # type: ignore
            refresh_token_value=character_token.refresh_token,
            client_session=session,
        )

        new_character_token = self.token_tool.character_token_from_oauth_token(
            oauth_token=refreshed_oauth_token
        )
        if new_character_token.character_id != character_token.character_id:
            raise RuntimeError(
                f"Refreshed token character ID {new_character_token.character_id} does "
                f"not match expected character ID {character_token.character_id}."
            )
        return new_character_token

    async def get_token(
        self, character_id: int, min_seconds: Annotated[int, Ge(0), Le(1200)] = 300
    ) -> CharacterToken:
        """Return the ESI token for the given character ID, optionally refreshing the token if it is about to expire.

        Args:
            character_id: The ID of the character for which to retrieve the token.
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. 0 to disable refresh. Default is 300 (5 minutes).

        Raises:
            KeyError: If no token for the given character ID exists.
        """
        if self._auth_store is None:
            raise RuntimeError("AuthStoreDisk context manager not entered.")
        if character_id not in self._auth_store.character_tokens:
            raise KeyError(f"No token found for character ID {character_id}.")
        if min_seconds < 0 or min_seconds > 1200:
            raise ValueError("min_seconds must be between 0 and 1200.")
        if min_seconds == 0:
            return self._auth_store.character_tokens[character_id]
        character_token = self._auth_store.character_tokens[character_id]
        if character_token.expires_in >= min_seconds:
            return character_token

        async with aiohttp.ClientSession() as session:
            new_character_token = await self._refresh_character_token(
                character_token, session
            )

        self._auth_store.character_tokens[new_character_token.character_id] = (
            new_character_token
        )
        self._auth_store_dirty = True
        return new_character_token

    async def get_tokens(
        self, min_seconds: Annotated[int, Ge(0), Le(1200)] = 300
    ) -> dict[int, CharacterToken]:
        """Return a dict of all ESI tokens, optionally refreshing tokens that are about to expire.

        Args:
            min_seconds: The minimum number of seconds before a token expires to
                trigger a refresh. 0 to disable refresh. Default is 300 (5 minutes).

        Raises:
            KeyError: If no tokens exist.
        """
        ...

    def add_token(self, token: CharacterToken) -> None:
        """Add a new ESI token to the store.

        Raises:
            ValueError: If a token for the same character ID already exists.
        """
        ...

    async def remove_token(self, character_id: int) -> None:
        """Remove a token from the store by character ID.

        Removes the token from the store and revokes it with ESI.

        Raises:
            KeyError: If no token for the given character ID exists.
        """
        ...

    @property
    def client_id(self) -> str:
        """Return the client ID of the ESI application."""
        if self._auth_store is None:
            raise RuntimeError("AuthStoreDisk context manager not entered.")
        return self._auth_store.app_credentials.clientId


def init_auth_store(store_path: Path, credentials: EsiAppCredentials) -> None:
    """Initialize an empty auth store file on disk."""
    if store_path.exists():
        raise FileExistsError(f"Auth store file {store_path} already exists.")
    empty_store = AuthStore(app_credentials=credentials)
    data_root = AuthStoreRoot(root=empty_store)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(data_root.model_dump_json(indent=2))


def delete_auth_store(store_path: Path) -> None:
    """Delete the auth store file from disk."""
    if not store_path.exists():
        raise FileNotFoundError(f"Auth store file {store_path} does not exist.")
    if not store_path.is_file():
        raise RuntimeError(f"Auth store path {store_path} is not a file.")
    if not store_path.suffix == ".json":
        raise RuntimeError(
            f"Auth store file {store_path} does not have a .json extension."
        )
    store_path.unlink()
