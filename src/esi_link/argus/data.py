"""ArgusData manages access to data stored by Argus."""

from dataclasses import dataclass
from pathlib import Path

from eve_static_data import SdeYamlDatasetLoader

from esi_link.argus.derived_data import DerivedLoader


@dataclass
class ArgusDataStatus:
    """Status of the Argus data."""

    sde_path: Path
    derived_path: Path
    build_number: int | None = None
    release_date: str | None = None


class ArgusData:
    def __init__(self, sde_path: Path, derived_path: Path | None = None):
        self.sde_path = sde_path
        self._derived_path = derived_path or sde_path / "derived"
        self._sde_loader = SdeYamlDatasetLoader(sde_path)
        self._derived_loader = DerivedLoader(self._derived_path)

    @property
    def sde_loader(self) -> SdeYamlDatasetLoader:
        """Get an SDELoader instance based on the settings."""
        return self._sde_loader

    @property
    def derived_datasets(self) -> DerivedLoader:
        """Get a loader for derived datasets."""
        return self._derived_loader

    def status(self) -> ArgusDataStatus:
        """Get the status of the app sde data."""
        # TODO return buildNumber and releaseDate from the app sde data.
        return ArgusDataStatus(sde_path=self.sde_path, derived_path=self._derived_path)


class ArgusDataImporter:
    """ArgusDataImporter is responsible for importing data into the Argus app."""

    def __init__(self, app_sde_path: ArgusData):
        self.app_sde_path = app_sde_path

    def import_sde(self, sde_path: Path) -> None:
        """Import SDE data from the specified path.

        Import SDE data from the specified folder. This will replace any existing data in
        the app's SDE directory. The provided path must contain the same structure as the
        EVE Static Data Export (SDE) yaml variant from CCP, with the files converted to
        json format. Any additional files or folders in the provided path will also be
        copied to the app's SDE directory, but only the expected SDE files will be loaded
        and made available through the dataset loader.

        Validation of the files (with Eve-Static-Data) is recommended before importing,
        but not required. If present, the validation report folder will also be copied
        to the app's SDE directory.

        Derived data files will be automatically generated from the imported SDE data
        and stored in the app's derived data directory. Any existing derived data will be
        replaced.
        """
        raise NotImplementedError("SDE import is not implemented yet.")

    def _generate_derived_data(self) -> None:
        """Generate derived data from the SDE data."""
        raise NotImplementedError("Derived data generation is not implemented yet.")
