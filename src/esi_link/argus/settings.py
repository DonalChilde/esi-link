"""Settings for Argus."""

from dataclasses import dataclass
from pathlib import Path

from eve_static_data import SdeYamlDatasetLoader
from eve_static_data.settings import (
    EveStaticDataSettings,
    EveStaticDataSettingsPydantic,
)
from eve_static_data.settings import get_settings as get_esd_settings
from pydantic import Field
from pydantic_settings import BaseSettings

from esi_link.argus import DEFAULT_APP_DIR
from esi_link.settings import EsiLinkSettings, EsiLinkSettingsPydantic
from esi_link.settings import get_settings as get_esi_link_settings


@dataclass
class ArgusSettings:
    """Settings for Argus."""

    application_directory: Path
    sde_directory: Path
    # log_directory: Path
    esd_settings: EveStaticDataSettings
    esi_link_settings: EsiLinkSettings

    def sde_loader(self) -> SdeYamlDatasetLoader:
        """Get an SDELoader instance based on the settings."""
        return SdeYamlDatasetLoader(
            self.sde_directory,
        )


class ArgusSettingsPydantic(BaseSettings):
    """Pydantic settings for Argus."""

    # NOTE This is a stub for when Argus is split from ESI Link.
    # At that time, this class will need enought fields to recreate an EsiLinkSettings instance.

    application_directory: Path = Field(
        default=DEFAULT_APP_DIR,
        description="The directory where Argus will store its data and logs.",
    )
    sde_directory: Path = Field(
        default=DEFAULT_APP_DIR / "sde",
        description="The directory where the EVE Static Data Export (SDE) is stored.",
    )
    log_directory: Path = Field(
        default=DEFAULT_APP_DIR / "logs",
        description="The directory where Argus will store its logs.",
    )

    # model_config = SettingsConfigDict(
    #     env_file=(
    #         f"{DEFAULT_APP_DIR}/.esi-link.env",
    #         ".esi-link.env",
    #     ),
    #     env_prefix=_app_env_prefix,
    # )


# FIXME: the way the esi-link and esd settings models are initialized here is flawed.
# using get settings does not cascade the directory settings for subdirs under application direcrtory.
# This will be an issue when argus splits from esi-link, right now the proper settings
# objects will be set in the callback.


def get_settings() -> ArgusSettings:
    """Get the settings for Argus."""
    argus_pydantic_settings = ArgusSettingsPydantic()
    esi_link_settings_pydantic = EsiLinkSettingsPydantic()
    esd_settings_pydantic = EveStaticDataSettingsPydantic()
    esd_settings_pydantic.application_directory = (
        argus_pydantic_settings.application_directory / "eve-static-data"
    )
    # This should cascade the esi-link directory settings under the argus application directory.
    esi_link_settings_pydantic.app_dir = (
        argus_pydantic_settings.application_directory / "esi-link"
    )
    esi_link_settings = get_esi_link_settings(
        pydantic_settings=esi_link_settings_pydantic
    )

    esd_settings = get_esd_settings(pydantic_settings=esd_settings_pydantic)
    argus_settings = ArgusSettings(
        application_directory=argus_pydantic_settings.application_directory,
        sde_directory=argus_pydantic_settings.sde_directory,
        esd_settings=esd_settings,
        esi_link_settings=esi_link_settings,
    )
    return argus_settings
