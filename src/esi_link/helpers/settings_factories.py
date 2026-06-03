"""Factory functions for creating instances of settings-related classes."""

from esi_link.auth.oauth_metadata import OAuthMetadataDiskCache
from esi_link.auth.token_store import TokenStore
from esi_link.auth.token_tool import TokenTool
from esi_link.protocols.cache_manager import CacheManagerProtocol
from esi_link.schema.schema_cache import SchemaCache
from esi_link.settings import EsiLinkSettings


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


def schema_cache_factory(settings: EsiLinkSettings) -> SchemaCache:
    """Factory function to create a SchemaCache instance."""
    return SchemaCache(cache_directory=settings.schema_cache_directory)


def web_cache_factory(settings: EsiLinkSettings) -> CacheManagerProtocol:
    """Factory function to create a web cache instance based on the cache configuration in settings."""
    cache_config = settings.cache_configuration
    if cache_config.cache_type == "memory":
        raise NotImplementedError("In-memory cache is not yet implemented.")
    elif cache_config.cache_type == "diskcache":
        from esi_link.cache.diskcache_cache import DiskCache

        return DiskCache(cache_directory=settings.cache_directory / "diskcache_cache")
    elif cache_config.cache_type == "jsonstore":
        from esi_link.cache.json_disk_cache import JsonDiskCache

        return JsonDiskCache(
            cache_directory=settings.cache_directory / "json_disk_cache"
        )
    else:
        raise ValueError(f"Unsupported cache type: {cache_config.cache_type}")
