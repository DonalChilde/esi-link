"""Settings for Argus."""

from dataclasses import dataclass
from pathlib import Path

from eve_static_data import SDELoader
from eve_static_data.settings import EveStaticDataSettings
from pydantic_settings import BaseSettings

from esi_link.settings import EsiLinkSettings


@dataclass
class ArgusSettings:
    """Settings for Argus."""

    application_directory: Path
    sde_directory: Path
    # log_directory: Path
    esd_settings: EveStaticDataSettings
    esi_link_settings: EsiLinkSettings

    def sde_loader(self) -> SDELoader:
        """Get an SDELoader instance based on the settings."""
        return SDELoader(
            self.sde_directory,
            derived_datasets_path=self.sde_directory / "derived_datasets",
        )


class ArgusSettingsPydantic(BaseSettings):
    """Pydantic settings for Argus."""

    # NOTE This is a stub for when Argus is split from ESI Link.
    # At that time, this class will need enought fields to recreate an EsiLinkSettings instance.

    application_directory: Path
    sde_directory: Path

    # model_config = SettingsConfigDict(
    #     env_file=(
    #         f"{DEFAULT_APP_DIR}/.esi-link.env",
    #         ".esi-link.env",
    #     ),
    #     env_prefix=_app_env_prefix,
    # )


def get_settings() -> ArgusSettings:
    """Get the settings for Argus."""
    raise NotImplementedError("Argus settings are not implemented yet.")
    pydantic_settings = ArgusSettingsPydantic()
    esi_link_settings = EsiLinkSettings.from_pydantic(pydantic_settings)
    return ArgusSettings(
        application_directory=pydantic_settings.application_directory,
        sde_directory=pydantic_settings.sde_directory,
        esi_link_settings=esi_link_settings,
    )
