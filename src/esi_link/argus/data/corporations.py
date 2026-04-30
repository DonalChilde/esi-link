from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

from pydantic import RootModel


@dataclass(slots=True)
class Corporation:
    id: int
    name: str


CorporationRoot = RootModel[dict[int, Corporation]]


class CorporationsDisk:
    def __init__(self, corporations_path: Path):
        self.corporations_path = corporations_path
        self._corporations: dict[int, Corporation] | None = None
        self._corporations_dirty: bool = False

    def __enter__(self) -> Self:
        """Load the corporations from disk, or initialize an empty cache if the file doesn't exist."""
        if self._corporations is not None:
            raise RuntimeError("CorporationsDisk context manager already entered.")
        if self.corporations_path.exists():
            if not self.corporations_path.is_file():
                raise RuntimeError(
                    f"Corporations path {self.corporations_path} is not a file."
                )
            self._corporations = CorporationRoot.model_validate_json(
                self.corporations_path.read_text()
            ).root
        else:
            self._corporations = {}
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Save the corporations to disk if they were modified during the context."""
        if self._corporations is None:
            raise RuntimeError("CorporationsDisk context manager not entered.")
        if not self._corporations_dirty:
            self._corporations = None
            return
        data_root = CorporationRoot(root=self._corporations)
        self.corporations_path.write_text(data_root.model_dump_json(indent=2))
        self._corporations = None

    def get(self, id: int) -> Corporation | None:
        """Get the corporation for the given ID, or None if it's not in the cache."""
        if self._corporations is None:
            raise RuntimeError("CorporationsDisk context manager not entered.")
        return self._corporations.get(id)

    def set(self, corporation: Corporation) -> None:
        """Set the corporation for the given ID."""
        if self._corporations is None:
            raise RuntimeError("CorporationsDisk context manager not entered.")
        self._corporations[corporation.id] = corporation
        self._corporations_dirty = True

    def corporations(self) -> dict[int, Corporation]:
        """Get the entire corporations cache."""
        if self._corporations is None:
            raise RuntimeError("CorporationsDisk context manager not entered.")
        return self._corporations
