"""Factory function to create EsiLink instances."""

from esi_auth.esi_auth import TokenManager

from esi_link import USER_AGENT
from esi_link.cache_p import cache_factory
from esi_link.download_esi_schema import download_esi_schema
from esi_link.esi_http import EsiHttpRateLimited
from esi_link.esi_link import EsiLink
from esi_link.models import EsiSchema
from esi_link.response_handlers import HandlerManager
from esi_link.settings import EsiLinkSettings


def esi_link_factory(
    settings: EsiLinkSettings, esi_schema: EsiSchema | None = None
) -> EsiLink:
    """Factory function to create an EsiLink instance based on the provided configuration."""
    if esi_schema is None:
        esi_schema = download_esi_schema(
            url=settings.esi_schema_url,
            headers={"User-Agent": USER_AGENT},
        )
    if not settings.auth_connection_string():
        token_manager = None
    else:
        token_manager = TokenManager(
            connection_string=settings.auth_connection_string()
        )
    cache = cache_factory(settings.cache_connection_string)
    esi_http = EsiHttpRateLimited(
        cache=cache,
        esi_schema=esi_schema,
        max_rate=settings.connection_max_rate,
        time_period=settings.connection_period,
    )
    esi_link = EsiLink(
        esi_schema=esi_schema,
        esi_http=esi_http,
        handler_manager=HandlerManager(),
        token_manager=token_manager,
    )
    return esi_link
