from pathlib import Path

from esi_auth.esi_auth import TokenManager

from esi_link.cache_p import cache_factory
from esi_link.esi_http import EsiHttpRateLimited
from esi_link.esi_link import EsiLink
from esi_link.models import EsiLinkConfig
from esi_link.response_handlers import HandlerManager


def esi_link_factory(config: EsiLinkConfig) -> EsiLink:
    """Factory function to create an EsiLink instance based on the provided configuration."""
    if config.esi_schema is None:
        raise ValueError("ESI schema must be provided in the configuration.")
    if config.esi_auth_connection_string is None:
        token_manager = None
    else:
        token_manager = TokenManager(store_path=Path(config.esi_auth_connection_string))
    cache = cache_factory(config.cache_connection_string)
    esi_http = EsiHttpRateLimited(
        cache=cache,
        esi_schema=config.esi_schema,
        max_rate=config.connection_max_rate,
        time_period=config.connection_period,
    )
    esi_link = EsiLink(
        esi_schema=config.esi_schema,
        esi_http=esi_http,
        handler_manager=HandlerManager(),
        token_manager=token_manager,
    )
    return esi_link
