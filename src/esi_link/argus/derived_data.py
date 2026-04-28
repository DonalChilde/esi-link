"""DerivedLoader is responsible for loading derived data from a specified path."""

from enum import StrEnum
from pathlib import Path

from eve_static_data.models import yaml_datasets as YD
from eve_static_data.models import yaml_records as YR
from pydantic import RootModel


class DerivedFiles(StrEnum):
    """Enum for derived file names."""

    PUBLISHED_TYPES = "published_types"
    PUBLISHED_BLUEPRINTS = "published_blueprints"

    def filename(self) -> str:
        """Get the filename for the derived data."""
        return f"{self.value}.json"


class DerivedLoader:
    def __init__(self, derived_path: Path):
        self.derived_path = derived_path

    def data_missing(self) -> list[DerivedFiles]:
        """Check that all expected derived dataset files exist and return a list of any that are missing."""
        missing_files = data_missing(self.derived_path)
        return missing_files

    def data_exists(self) -> list[DerivedFiles]:
        """Check if any derived dataset files exist."""
        existing_files = data_exists(self.derived_path)
        return existing_files

    def _load_root_model[T](
        self, filename: str, root_model_type: type[RootModel[T]]
    ) -> RootModel[T]:
        """Load a root model from a file."""
        file_path = self.derived_path / filename
        if not file_path.is_file():
            raise ValueError(f"Derived data file {file_path} does not exist.")
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return root_model_type.model_validate_json(f.read())
        except Exception as e:
            raise ValueError(
                f"Failed to load derived data from {file_path}. {e}"
            ) from e

    def published_types(self) -> dict[int, YR.EveTypes]:
        """Load the published types."""
        root_model = YD.EveTypesRoot
        loaded_data = self._load_root_model(
            DerivedFiles.PUBLISHED_TYPES.filename(), root_model
        )
        return loaded_data.root

    def published_blueprints(self) -> dict[int, YR.Blueprints]:
        """Load the published blueprints."""
        root_model = YD.BlueprintsRoot
        loaded_data = self._load_root_model(
            DerivedFiles.PUBLISHED_BLUEPRINTS.filename(), root_model
        )
        return loaded_data.root


class DerivedWriter:
    def __init__(self, derived_path: Path):
        self.derived_path = derived_path
        try:
            self.derived_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(
                f"Derived path {derived_path} is not a directory or cannot be created."
            ) from e

    def data_exists(self) -> list[DerivedFiles]:
        """Check if any derived dataset files exist."""
        existing_files = data_exists(self.derived_path)
        return existing_files

    def data_missing(self) -> list[DerivedFiles]:
        """Check that all expected derived dataset files exist and return a list of any that are missing."""
        missing_files = data_missing(self.derived_path)
        return missing_files

    def reset_derived_data(self) -> None:
        """Reset the derived data by deleting all derived dataset files in the derived directory."""
        for derived_file in DerivedFiles:
            file_path = self.derived_path / derived_file.filename()
            if file_path.is_file():
                file_path.unlink()

    def _write_root_model[T](self, root_model: RootModel[T], filename: str) -> None:
        """Write a root model to a file."""
        file_path = self.derived_path / filename
        try:
            with file_path.open("x", encoding="utf-8") as f:
                f.write(root_model.model_dump_json(indent=2))
        except FileExistsError as e:
            raise ValueError(
                f"File {file_path} already exists. Derived data cannot be overwritten. Reset the derived store?"
            ) from e
        except Exception as e:
            raise ValueError(f"Failed to write derived data to {file_path}. {e}") from e

    def write_published_types(self, published_types: dict[int, YR.EveTypes]) -> None:
        """Write the published types to a file."""
        root_model = YD.EveTypesRoot(root=published_types)
        self._write_root_model(root_model, DerivedFiles.PUBLISHED_TYPES.filename())

    def write_published_blueprints(
        self, published_blueprints: dict[int, YR.Blueprints]
    ) -> None:
        """Write the published blueprints to a file."""
        root_model = YD.BlueprintsRoot(root=published_blueprints)
        self._write_root_model(root_model, DerivedFiles.PUBLISHED_BLUEPRINTS.filename())


def data_exists(derived_path: Path) -> list[DerivedFiles]:
    """Check if any derived dataset files exist."""
    existing_files: list[DerivedFiles] = []
    for derived_file in DerivedFiles:
        file_path = derived_path / derived_file.filename()
        if file_path.is_file():
            existing_files.append(derived_file)
    return existing_files


def data_missing(derived_path: Path) -> list[DerivedFiles]:
    """Check that all expected derived dataset files exist and return a list of any that are missing."""
    missing_files: list[DerivedFiles] = []
    for derived_file in DerivedFiles:
        file_path = derived_path / derived_file.filename()
        if not file_path.is_file():
            missing_files.append(derived_file)
    return missing_files


def published_types(eve_types: dict[int, YR.EveTypes]) -> dict[int, YR.EveTypes]:
    """Filter the provided types to only include those that are published."""
    published: dict[int, YR.EveTypes] = {}
    for type_id, eve_type in eve_types.items():
        if eve_type.published:
            published[type_id] = eve_type
    return published


def published_blueprints(
    eve_types: dict[int, YR.EveTypes], blueprints: dict[int, YR.Blueprints]
) -> dict[int, YR.Blueprints]:
    """Filter the provided blueprints to only include those that are published."""
    published: dict[int, YR.Blueprints] = {}
    published_type_ids = {
        type_id for type_id, eve_type in eve_types.items() if eve_type.published
    }
    for blueprint_id, blueprint in blueprints.items():
        if blueprint.blueprintTypeID in published_type_ids:
            published[blueprint_id] = blueprint
    return published
