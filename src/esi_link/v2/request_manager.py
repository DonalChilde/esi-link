"""Top level class for running ESI requests."""

from esi_link.v2.auth_provider import DummyAuthProvider
from esi_link.v2.esi_schema import load_schema_store
from esi_link.v2.json_disk_cache import JsonDiskCache
from esi_link.v2.settings import get_settings


class EsiLink:
    def __init__(self) -> None:
        """Initialize the EsiLink instance."""
        self.settings = get_settings()
        self.schema_store = load_schema_store()
        self.auth_provider = DummyAuthProvider()
        self.cache = JsonDiskCache(cache_directory=self.settings.json_cache_directory)
