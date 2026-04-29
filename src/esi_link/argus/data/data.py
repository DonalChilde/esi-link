"""ArgusData manages access to data stored by Argus."""

import logging
from dataclasses import dataclass
from pathlib import Path

from eve_static_data import SdeYamlDatasetLoader

from esi_link.argus.data import derived_data as DD

logger = logging.getLogger(__name__)


@dataclass
class ArgusDataStatus:
    """Status of the Argus data."""

    sde_path: Path
    derived_path: Path
    build_number: int | None = None
    release_date: str | None = None


class ArgusDataLoader:
    def __init__(self, sde_path: Path, derived_path: Path | None = None):
        """ArgusDataLoader is responsible for loading data for the Argus app.

        Data must be available at time of creation.
        """
        self.sde_path = sde_path
        self._derived_path = derived_path or sde_path / "derived"
        self._sde_loader = self._init_sde_loader()
        self._derived_loader = self._init_derived_loader()

    def _init_sde_loader(self) -> SdeYamlDatasetLoader:
        """Initialize the SDE loader."""
        try:
            return SdeYamlDatasetLoader(self.sde_path)
        except Exception as e:
            raise ValueError(
                f"Failed to initialize SDE loader with path {self.sde_path} Do you need to import the sde? {e}"
            ) from e

    def _init_derived_loader(self) -> DD.DerivedLoader:
        """Initialize the derived data loader.

        Raises:
            ValueError: If any expected derived dataset files are missing, or if there is an error initializing the loader.
        """
        try:
            missing_files = DD.data_missing(self._derived_path)
            if missing_files:
                raise ValueError(
                    f"Missing derived dataset files: {', '.join(file.value for file in missing_files)}. Please ensure derived data is generated and available at {self._derived_path}."
                )
            return DD.DerivedLoader(self._derived_path)
        except Exception as e:
            raise ValueError(
                f"Failed to initialize derived data loader with path {self._derived_path}. {e}"
            ) from e

    @property
    def sde_loader(self) -> SdeYamlDatasetLoader:
        """Get an SDELoader instance based on the settings."""
        return self._sde_loader

    @property
    def derived_dataset_loader(self) -> DD.DerivedLoader:
        """Get a loader for derived datasets."""
        return self._derived_loader

    def status(self) -> ArgusDataStatus:
        """Get the status of the app sde data."""
        return ArgusDataStatus(
            sde_path=self.sde_path,
            derived_path=self._derived_path,
            build_number=self.sde_loader.buildNumber,
            release_date=self.sde_loader.releaseDate,
        )


class ArgusDataImporter:
    def __init__(self, sde_destination_path: Path, derived_data_path: Path):
        """ArgusDataImporter is responsible for importing data into the Argus app."""
        self.sde_destination_path = sde_destination_path
        self.derived_data_path = derived_data_path

    def _check_valid_import_path(self, sde_import_path: Path) -> None:
        """Check the validity of the imported data.

        Attempts to validate import data using the SdeYamlDatasetLoader.
        """
        try:
            # SdeYamlDatasetLoader creation will fail if the import path does not contain
            # a valid `_sde.yaml/json` file. It does not automatically check for the rest
            # of the expected SDE files.
            loader = SdeYamlDatasetLoader(sde_import_path)
            if loader.file_type != ".json":
                raise ValueError(
                    f"Expected json files in the SDE import path, but found {loader.file_type} files. Please export to json first."
                )
        except Exception as e:
            logger.error(
                f"Data import validation failed for import path {sde_import_path}: {e}"
            )
            raise e

    def _check_valid_destination_path(self, sde_destination_path: Path) -> None:
        """Check that the import destination path is valid."""
        # Checks for files or directories in the app's SDE directory. If any are found,
        # checks for a valid _sde.json file to make a basic check that the path should be
        # considered as containing existing SDE data. This is to prevent accidental deletion
        # of unrelated files in a directory that may have been misconfigured as the app's SDE path.
        if sde_destination_path.exists() and sde_destination_path.is_file():
            logger.error(
                f"Import destination path {sde_destination_path} is an existing file, and should be a directory."
            )
            raise ValueError(
                f"Import destination path {sde_destination_path} is an existing file, and should be a directory."
            )
        if (
            sde_destination_path.exists()
            and sde_destination_path.is_dir()
            and any(sde_destination_path.iterdir())
        ):
            try:
                loader = SdeYamlDatasetLoader(sde_destination_path)
                if loader.file_type != ".json":
                    raise ValueError(
                        f"Expected json files in the app's SDE directory, but found {loader.file_type} files. Please check the app's SDE path configuration."
                    )
            except Exception as e:
                logger.error(
                    f"Existing data validation failed for the app's SDE directory at {sde_destination_path}: {e}"
                )
                raise e

    def _clear_existing_data(self, sde_destination_path: Path) -> None:
        """Clear existing data in the app's SDE directory."""
        # Deletes all files and directories in the app's SDE directory. This is to ensure a clean
        # slate for the new data import, and to prevent any potential conflicts or issues with
        # leftover files from previous imports. The check for valid existing data is done
        # to prevent accidental deletion of unrelated files in a misconfigured SDE path.
        self._check_valid_destination_path(sde_destination_path)
        if sde_destination_path.exists() and sde_destination_path.is_dir():
            for item in sde_destination_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    for sub_item in item.rglob("*"):
                        if sub_item.is_file():
                            sub_item.unlink()
                        elif sub_item.is_dir():
                            sub_item.rmdir()
                    item.rmdir()

    def _copy_import_data(
        self, sde_import_path: Path, sde_destination_path: Path
    ) -> None:
        """Copy data from the import path to the app's SDE directory."""
        # Copies all files and directories from the import path to the app's SDE directory. This
        # includes both the expected SDE files that will be loaded by the app, as well as any
        # additional files or folders that may be present in the import path. This is to ensure
        # that any relevant data, such as validation reports, is also copied over during the import process.
        for item in sde_import_path.iterdir():
            dest = sde_destination_path / item.name
            if item.is_file():
                dest.write_bytes(item.read_bytes())
            elif item.is_dir():
                if dest.exists():
                    logger.warning(
                        f"Destination directory {dest} already exists. Contents may be overwritten."
                    )
                else:
                    dest.mkdir()
                self._copy_import_data(item, dest)

    def import_sde(self, sde_import_path: Path) -> None:
        """Import SDE data from the specified path.

        Import SDE data from the specified folder. This will replace any existing data in
        the app's SDE directory. The provided path must contain the same structure as the
        EVE Static Data Export (SDE) yaml variant from CCP, with the files converted to
        json format. Any additional files or folders in the provided path will also be
        copied to the app's SDE directory, but only the expected SDE files will be loaded
        and made available through the dataset loader.

        Validation of the files (with Eve-Static-Data) is recommended before importing,
        but not required. If present in the SDE import directory, the validation report
        directory will also be copied to the app's SDE directory.

        Derived data files will be automatically generated from the imported SDE data
        and stored in the app's derived data directory. Any existing derived data will be
        replaced.
        """
        self._check_valid_import_path(sde_import_path)
        self.sde_destination_path.mkdir(parents=True, exist_ok=True)
        # This also checks to ensure the destination path is valid before deleting any
        # existing data, to prevent accidental deletion of unrelated files in a misconfigured SDE path.
        self._clear_existing_data(self.sde_destination_path)
        self._copy_import_data(sde_import_path, self.sde_destination_path)

        self._generate_derived_data()

    def _generate_derived_data(self) -> None:
        """Generate derived data from the SDE data."""
        loader = SdeYamlDatasetLoader(self.sde_destination_path)
        writer = DD.DerivedWriter(self.derived_data_path)
        writer.reset_derived_data()

        # Load datasets needed for deriving.
        eve_types = DD.published_types(loader.eve_types().root)
        blueprints = DD.published_blueprints(eve_types, loader.blueprints().root)

        # Write derived datasets.
        writer.write_published_types(eve_types)
        writer.write_published_blueprints(blueprints)
