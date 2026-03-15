import logging

import aiohttp
from aiolimiter import AsyncLimiter

from esi_link.v3.models import (
    CachedResponse,
    CachedResponseStatus,
    HttpResponse,
    Response,
    RuntimeRequest,
)
from esi_link.v3.protocols import CacheManagerProtocol, HttpRequestExecutorProtocol

logger = logging.getLogger(__name__)


class RequestExecutor(HttpRequestExecutorProtocol):
    def __init__(
        self,
        cache_manager: CacheManagerProtocol,
        rate_limiter: AsyncLimiter,
    ):
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter

    async def __call__(
        self, request: RuntimeRequest, session: aiohttp.ClientSession
    ) -> Response:
        """Execute the given request, utilizing caching and rate limiting."""
