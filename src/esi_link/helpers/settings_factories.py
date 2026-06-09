"""Factory functions for creating instances of settings-related classes."""

from esi_link.protocols.cache_manager import CacheManagerProtocol
from esi_link.settings import EsiLinkSettings


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


def app_data_db_uri_factory(settings: EsiLinkSettings) -> str:
    """Factory function to create the URI for the app-data SQLite database."""
    return f"file:{settings.app_data_db_path}?mode=rwc"
