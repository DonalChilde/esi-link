"""File operations for JSON files, including reading and writing JSON data."""

import json
from collections.abc import Iterable
from pathlib import Path

from .file_access_protocols import FileReaderProtocol, FileWriterProtocol

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | dict[str, "JsonValue"] | list["JsonValue"]


class JsonFileWriter(FileWriterProtocol[JsonValue]):
    """Concrete implementation of FileWriterProtocol for writing JSON data."""

    def __init__(
        self,
        path_out: Path,
        *,
        overwrite: bool = False,
        is_file: bool = True,
        indent: int = 2,
    ) -> None:
        super().__init__(path_out, overwrite=overwrite, binary=False, is_file=is_file)
        self.indent = indent

    def write(self, data: JsonValue) -> int:
        """Write the provided dictionary as JSON to the file."""
        if self.fp is None:
            raise ValueError("File is not open for writing.")
        json.dump(data, self.fp, indent=self.indent)
        return 1

    def write_all(self, data: Iterable[JsonValue]) -> int:
        """Write_all is not implemented for JsonFileWriter."""
        raise NotImplementedError("write_all is not implemented for JsonFileWriter.")


class JsonFileReader(FileReaderProtocol[JsonValue]):
    """Concrete implementation of FileReaderProtocol for reading JSON data."""

    def __init__(
        self,
        path_in: Path,
        *,
        binary: bool = False,
        is_file: bool = True,
    ) -> None:
        super().__init__(path_in, binary=binary, is_file=is_file)

    def read(self) -> JsonValue:
        """Read JSON data from the file and return it as a Python object."""
        if self.fp is None:
            raise ValueError("File is not open for reading.")
        return json.load(self.fp)

    def read_all(self) -> Iterable[JsonValue]:
        """read_all is not implemented for JsonFileReader."""
        raise NotImplementedError("read_all is not implemented for JsonFileReader.")
