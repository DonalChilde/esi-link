from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

from pydantic import RootModel


@dataclass(slots=True)
class Character:
    id: int
    name: str


CharacterRoot = RootModel[dict[int, Character]]


class CharactersDisk:
    def __init__(self, characters_path: Path):
        self.characters_path = characters_path
        self._characters: dict[int, Character] | None = None
        self._characters_dirty: bool = False

    def __enter__(self) -> Self:
        """Load the characters from disk, or initialize an empty cache if the file doesn't exist."""
        if self._characters is not None:
            raise RuntimeError("CharactersDisk context manager already entered.")
        if self.characters_path.exists():
            if not self.characters_path.is_file():
                raise RuntimeError(
                    f"Characters path {self.characters_path} is not a file."
                )
            self._characters = CharacterRoot.model_validate_json(
                self.characters_path.read_text()
            ).root
        else:
            self._characters = {}
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Save the characters to disk if they were modified during the context."""
        if self._characters is None:
            raise RuntimeError("CharactersDisk context manager not entered.")
        if not self._characters_dirty:
            self._characters = None
            return
        data_root = CharacterRoot(root=self._characters)
        self.characters_path.write_text(data_root.model_dump_json(indent=2))
        self._characters = None

    def get(self, id: int) -> Character | None:
        """Get the character for the given ID, or None if it's not in the cache."""
        if self._characters is None:
            raise RuntimeError("CharactersDisk context manager not entered.")
        return self._characters.get(id)

    def set(self, character: Character) -> None:
        """Set the character for the given ID."""
        if self._characters is None:
            raise RuntimeError("CharactersDisk context manager not entered.")
        self._characters[character.id] = character
        self._characters_dirty = True

    def characters(self) -> dict[int, Character]:
        """Get the entire characters cache."""
        if self._characters is None:
            raise RuntimeError("CharactersDisk context manager not entered.")
        return self._characters
