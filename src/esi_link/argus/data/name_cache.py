"""A simple cache for names, to avoid making repeated calls to the ESI for the same ID.

Caches the results of PostUniverseNames. Can be saved to disk, as these names don't change often.

NameCache should be a context manager, so that updates to the cache can be saved to disk when the context is exited.

Future considerations:
- Add a TTL to the cache, so that entries can expire after a certain amount of time?
- Add a maximum size to the cache, and evict the least recently used entries when the cache is full?

"""

from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

from pydantic import RootModel

from esi_link.argus.models.esi_models import PostUniverseNamesItem


@dataclass(slots=True)
class CacheItem:
    item: PostUniverseNamesItem
    # last_accessed: str  # for potential future use in eviction policies
    # created_at: str  # for potential future use in TTL policies


CacheRoot = RootModel[dict[int, CacheItem]]


class NameCacheDisk:
    def __init__(self, cache_file: Path) -> None:
        """Initialize the NameCacheDisk with the given cache file path.

        This is a file based impementation of the NameCache, which will read from and
        write to the given cache file on disk.

        The cache file is loaded from disk when the context manager is entered, and saved
        to disk when the context manager is exited. The cache is only kept in memory
        while the context manager is active, and is cleared when the context manager is
        exited. Calls to the NameCache should be consolidated as much as feasible to avoid
        unnecessary disk I/O.
        """
        self._cache: dict[int, CacheItem] | None = None
        self._cache_file = cache_file
        self.cache_dirty: bool = False

    def get(self, id: int) -> PostUniverseNamesItem | None:
        """Get the name for the given ID, or None if it's not in the cache."""
        if self._cache is None:
            # indicates trying to use the cache before entering the context manager.
            raise RuntimeError("NameCache must be used as a context manager.")
        cache_item = self._cache.get(id)
        return cache_item.item if cache_item is not None else None

    def set(self, item: PostUniverseNamesItem) -> None:
        """Set the name for the given ID."""
        if self._cache is None:
            # indicates trying to use the cache before entering the context manager.
            raise RuntimeError("NameCache must be used as a context manager.")
        cache_item = CacheItem(item=item)
        self._cache[item.id_] = cache_item
        self.cache_dirty = True

    def __enter__(self) -> Self:
        """Load the cache from disk, or initialize an empty cache if the file doesn't exist."""
        if self._cache is not None:
            # indicates trying to enter the context manager when already entered.
            raise RuntimeError("NameCache context manager already entered.")
        if self._cache_file.exists():
            if not self._cache_file.is_file():
                raise RuntimeError(f"Cache file {self._cache_file} is not a file.")
            data_root = CacheRoot.model_validate_json(self._cache_file.read_text())
            self._cache = data_root.root
        else:
            self._cache = {}
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Save the cache to disk if it has been modified, and clear the cache from memory."""
        if self._cache is None:
            # indicates trying to exit the context manager when not entered.
            raise RuntimeError("NameCache context manager not entered.")
        if not self.cache_dirty:
            # no changes to the cache, so no need to write to disk.
            self._cache = None
            return
        data_root = CacheRoot(root=self._cache)
        self._cache_file.write_text(data_root.model_dump_json(indent=2))
        self._cache = None
