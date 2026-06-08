# AppData is an async context manager class that manages the database connection for the app-data db.

import sqlite3
from importlib.resources import files as resource_files
from types import TracebackType
from typing import Self

from httpx2 import AsyncClient, Client

from esi_link.app_data.helpers import transaction
from esi_link.auth.credential_manager_sqlite import CredentialManagerSqlite
from esi_link.auth.models import EsiAppCredentials
from esi_link.auth.oauth_metadata_sqlite import (
    OAuthMetadataSqliteCache,
    OAuthMetadataTimestamped,
)
from esi_link.auth.token_manager_sqlite import CharacterTokenManagerSqlite
from esi_link.auth.token_tool import TokenTool
from esi_link.schema.schema_cache_sqlite import SchemaCacheSqlite


class AppDataSqlite:
    def __init__(self, db_uri: str, session: Client, async_session: AsyncClient):
        self._db_uri = db_uri
        self._connection: sqlite3.Connection | None = None
        self._async_session = async_session
        self._session = session
        self._oauth_cache: OAuthMetadataSqliteCache | None = None
        self._credential_manager: CredentialManagerSqlite | None = None
        self._token_manager: CharacterTokenManagerSqlite | None = None
        self._schema_cache: SchemaCacheSqlite | None = None

    async def __aenter__(self) -> Self:
        """Initialize the database connection and set up related resources."""
        self._connection = self._make_connection()
        self._init_db()
        self._oauth_cache = OAuthMetadataSqliteCache(self._connection, self._session)
        self._credential_manager = CredentialManagerSqlite(self._connection)
        self._token_manager = self._init_token_manager()
        self._schema_cache = SchemaCacheSqlite(self._connection, self._session)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Clean up resources by closing the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
        self._oauth_cache = None
        self._credential_manager = None
        self._schema_cache = None
        self._token_manager = None
        return None

    def _init_token_manager(self) -> CharacterTokenManagerSqlite | None:
        """Initialize the token manager if credentials are available."""
        if self._connection is None:
            raise RuntimeError("Database connection is not established.")
        credentials = self.get_credentials()
        if credentials is None:
            return None
        token_tool = TokenTool(self.oauth_metadata)
        return CharacterTokenManagerSqlite(
            connection=self._connection,
            client_id=credentials.clientId,
            token_tool=token_tool,
        )

    def _make_connection(self) -> sqlite3.Connection:
        """Create a new connection to the app-data database."""
        # Keep SQLite in autocommit mode so explicit BEGIN/COMMIT in
        # app_data.helpers.transaction is the only transaction boundary.
        connection = sqlite3.connect(self._db_uri, uri=True, autocommit=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        """Initialize the database schema if it doesn't exist."""
        if self._connection is None:
            raise RuntimeError("Database connection is not established.")
        table_defs = (
            resource_files("esi_link.app_data").joinpath("table_defs.sql").read_text()
        )
        with transaction(self._connection) as conn:
            conn.executescript(table_defs)

    @property
    def token_manager(self) -> CharacterTokenManagerSqlite | None:
        """Get the token manager, which may be None if credentials are not set."""
        return self._token_manager

    def get_credentials(self) -> EsiAppCredentials | None:
        """Get the ESI app credentials from the database."""
        if self._credential_manager is None:
            raise RuntimeError("Credential manager is not initialized.")
        return self._credential_manager.get()

    def save_credentials(
        self, credentials: EsiAppCredentials, overwrite: bool = False
    ) -> None:
        """Save the ESI app credentials to the database."""
        if self._credential_manager is None:
            raise RuntimeError("Credential manager is not initialized.")
        self._credential_manager.save(credentials, overwrite=overwrite)
        # If credentials are updated, we need to reinitialize the token manager to use
        # the new client ID.
        self._token_manager = self._init_token_manager()

    @property
    def oauth_metadata(self) -> OAuthMetadataTimestamped:
        """Get the current OAuth metadata, either from cache or freshly fetched."""
        if self._oauth_cache is None:
            raise RuntimeError("OAuth metadata cache is not initialized.")
        return self._oauth_cache.get()

    @property
    def schema_cache(self) -> SchemaCacheSqlite:
        if self._schema_cache is None:
            raise RuntimeError("Schema cache is not initialized.")
        return self._schema_cache

    @property
    def web_cache(self):
        pass
