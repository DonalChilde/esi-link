# AppData is an async context manager class the db connection for the app-data db.

from types import TracebackType
from typing import Self


class AppDataSqlite:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.db = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        pass

    @property
    def token_store(self):
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
