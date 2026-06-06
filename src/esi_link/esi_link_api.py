from contextlib import AsyncExitStack
from types import TracebackType

from httpx2 import AsyncClient, Client

from esi_link.auth.token_store import TokenStore
from esi_link.helpers.http_client import config_async_http_client, config_http_client
from esi_link.helpers.settings_factories import (
    schema_cache_factory,
    token_store_factory,
    web_cache_factory,
)
from esi_link.request.models import Request, RequestGroup
from esi_link.request_dispatch_esi_link import (
    dispatch_request,
    dispatch_request_group,
)
from esi_link.response.models import ResponseDebugGroup, ResponseGroup
from esi_link.settings import EsiLinkSettings


class EsiLink:
    def __init__(self, settings: EsiLinkSettings):
        self._settings = settings
        self._session: Client | None = None
        self._async_session: AsyncClient | None = None
        self._stack = AsyncExitStack()
        # instance resources
        self._cache = web_cache_factory(settings)
        self._token_store: TokenStore | None = None
        self._schema_cache = schema_cache_factory(settings)

    async def __aenter__(self):
        # Initialize resources here if needed
        self._session = self._stack.enter_context(config_http_client())
        self._token_store = self._stack.enter_context(
            token_store_factory(self._settings)
        )
        self._async_session = await self._stack.enter_async_context(
            await config_async_http_client()
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        # This automatically calls __exit__ on all contained context managers
        # and forwards any exceptions correctly
        return await self._stack.__aexit__(exc_type, exc_value, traceback)

    async def send_request(
        self, request: Request
    ) -> tuple[ResponseGroup, ResponseDebugGroup | None]:
        if not self._session or not self._async_session:
            raise ValueError(
                "EsiLink instance must be used as an async context manager to send requests."
            )

        return await dispatch_request(
            request=request,
            schema_cache=self._schema_cache,
            web_cache=self._cache,
            session=self._session,
            async_session=self._async_session,
            token_store=self._token_store,
        )

    async def send_request_group(
        self, request_group: RequestGroup
    ) -> tuple[ResponseGroup, ResponseDebugGroup | None]:
        if not self._session or not self._async_session:
            raise ValueError(
                "EsiLink instance must be used as an async context manager to send requests."
            )

        return await dispatch_request_group(
            request_group=request_group,
            schema_cache=self._schema_cache,
            web_cache=self._cache,
            session=self._session,
            async_session=self._async_session,
            token_store=self._token_store,
        )
