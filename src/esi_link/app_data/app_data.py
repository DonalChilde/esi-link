# AppData is an async context manager class the db connection for the app-data db.

import sqlite3
from contextlib import contextmanager
from importlib.resources import files as resource_files
from types import TracebackType
from typing import Self

from esi_link.app_data.helpers import transaction


class AppDataSqlite:
    def __init__(self, db_uri: str):
        self.db_uri = db_uri
        self.connection: sqlite3.Connection | None = None

    async def __aenter__(self) -> Self:
        self.connection = self._make_connection()
        self._init_db()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def _make_connection(self) -> sqlite3.Connection:
        """Create a new connection to the app-data database."""
        connection = sqlite3.connect(self.db_uri, uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        """Initialize the database schema if it doesn't exist."""
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")
        table_defs = (
            resource_files("esi_link.app_data").joinpath("table_defs.sql").read_text()
        )
        with transaction(self.connection) as conn:
            conn.executescript(table_defs)
        self.connection.commit()

    @property
    async def token_store(self):
        pass

    @property
    def oauth_metadata(self):
        pass

    @property
    def schema_store(self):
        pass

    @property
    def web_cache(self):
        pass
