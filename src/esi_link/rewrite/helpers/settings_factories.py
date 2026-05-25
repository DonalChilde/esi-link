"""Factory functions for creating instances of settings-related classes."""

from esi_link.rewrite.auth.oauth_metadata import OAuthMetadataDiskCache
from esi_link.rewrite.auth.token_store import TokenStore
from esi_link.rewrite.auth.token_tool import TokenTool
from esi_link.rewrite.settings import EsiLinkSettings


def metadata_cache_factory(settings: EsiLinkSettings) -> OAuthMetadataDiskCache:
    """Factory function to create an OAuthMetadataDiskCache instance."""
    return OAuthMetadataDiskCache(
        settings.auth_metadata_cache_path, settings.auth_metadata_cache_ttl
    )


def token_tool_factory(settings: EsiLinkSettings) -> TokenTool:
    """Factory function to create a TokenTool instance."""
    metadata_cache = metadata_cache_factory(settings)
    with metadata_cache:
        metadata = metadata_cache.metadata
    return TokenTool(metadata)


def token_store_factory(settings: EsiLinkSettings) -> TokenStore:
    """Factory function to create a TokenStore instance."""
    token_tool = token_tool_factory(settings)
    return TokenStore(store_path=settings.token_store_path, token_tool=token_tool)
