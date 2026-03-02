from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import IO, Any, Protocol, Self, TypeVar

T = TypeVar("T")


class FileWriterProtocol[T](Protocol):
    """Protocol for writer implementations that support context management."""

    # Protocol instance attributes must be explicitly declared here.
    path_out: Path
    overwrite: bool
    binary: bool
    is_file: bool
    fp: IO[Any] | None = None  # File-like object for writing, initialized in __enter__

    def __init__(
        self,
        path_out: Path,
        *,
        overwrite: bool = False,
        binary: bool = False,
        is_file: bool = True,
    ) -> None:
        """Define the expected initializer signature for implementations.

        The typical implementation will write to a file at the sepcified path_out,
        but the is_file flag allows for the possibility of writing to a directory
        or other non-file target if needed.

        Args:
            path_out: The output file path.
            overwrite: Whether to overwrite existing files.
            binary: Whether to write in binary mode.
            is_file: Whether the path_out is a file (vs. a directory).
        """
        self.path_out = path_out
        self.overwrite = overwrite
        self.binary = binary
        self.is_file = is_file
        self.fp = None  # Initialize file-like object to None, will be set in __enter__

    def __enter__(self) -> Self:
        """Enter context and return the writer instance."""
        mode = self._get_mode()
        self.fp = open(self.path_out, mode)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context and release resources."""
        if self.fp is not None:
            self.fp.close()
        self.fp = None

    def _get_mode(self) -> str:
        """Determine the file mode string based on overwrite and binary flags."""
        mode = "x" if self.overwrite else "w"
        if self.binary:
            mode += "b"
        return mode

    def write(self, data: T) -> int:
        """Write a chunk of data and return bytes/units written."""
        ...

    def write_all(self, data: Iterable[T]) -> int:
        """Write all data, handling partial writes internally."""
        ...


class FileReaderProtocol[T](Protocol):
    """Protocol for reader implementations that support context management."""

    # Protocol instance attributes must be explicitly declared here.
    path_in: Path
    binary: bool
    is_file: bool
    fp: IO[Any] | None = None  # File-like object for reading, initialized in __enter__

    def __init__(
        self,
        path_in: Path,
        *,
        binary: bool = False,
        is_file: bool = True,
    ) -> None:
        """Define the expected initializer signature for implementations.

        The typical implementation will read from a file at the sepcified path_in,
        but the is_file flag allows for the possibility of reading from a directory
        or other non-file target if needed.

        Args:
            path_in: The input file path.
            binary: Whether to read in binary mode.
            is_file: Whether the path_in is a file (vs. a directory).
        """
        self.path_in = path_in
        self.binary = binary
        self.is_file = is_file
        self.fp = None  # Initialize file-like object to None, will be set in __enter__

    def __enter__(self) -> Self:
        """Enter context and return the reader instance."""
        mode = "rb" if self.binary else "r"
        self.fp = open(self.path_in, mode)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context and release resources."""
        if self.fp is not None:
            self.fp.close()
        self.fp = None

    def read(self) -> T:
        """Read a chunk of data and return it."""
        ...

    def read_all(self) -> Iterable[T]:
        """Read all data and return it as an iterable."""
        ...
