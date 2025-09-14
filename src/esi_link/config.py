"""A configuration object using pydantic-settings for Esi Link"""

from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from typer import get_app_dir
from whenever import Instant

from esi_link.helpers.make_safe_env_name import make_safe_env_name

APP_NAMESPACE = "pfmsoft"
APP_NAME = "Esi Link"

_app_dir = get_app_dir(app_name=f"{APP_NAMESPACE}_{APP_NAME}", force_posix=True)
_app_env_prefix = make_safe_env_name(f"{APP_NAMESPACE}_{APP_NAME}_")


class CacheType(StrEnum):
    FILE = "file"
    MEMORY = "memory"
    SQLITE = "sqlite"


class AppConfig(BaseSettings):
    name: str
    app_dir: Path = Path(_app_dir)
    log_dir: Path = app_dir / "logs"
    data_dir: Path = app_dir / "data"
    schema_dir: Path = app_dir / "schema"
    cache_dir: Path = app_dir / "cache"
    temp_dir: Path = app_dir / "temp"

    cache_type: CacheType = CacheType.FILE
    cache_file: Path = cache_dir / "esi_cache.json"

    app_secret: str = ""
    client_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=(
            f"{_app_dir}/.env",
            f"{_app_dir}/.secrets.env",
            ".env",
            ".secrets.env",
        ),
        env_prefix=_app_env_prefix,
    )

    def __str__(self) -> str:
        return (
            f"name={self.name}\n"
            f"app_dir={self.app_dir}\n"
            f"log_dir={self.log_dir}\n"
            f"data_dir={self.data_dir}\n"
            f"schema_dir={self.schema_dir}\n"
            f"cache_dir={self.cache_dir}\n"
            f"temp_dir={self.temp_dir}\n"
            f"app_secret={self.app_secret}\n"
            f"client_secret={self.client_secret}\n"
        )


def init_env_file(dir_path: Path, file_name: str = ".env", overwrite: bool = False):
    """Initialize a .env file in the specified directory if it does not exist."""
    env_path = dir_path / file_name
    if env_path.exists() and not overwrite:
        raise ValueError(
            f"Environment file already exists at {env_path}, and overwrite not selected."
        )
    if env_path.is_dir():
        raise ValueError(f"Environment file path {env_path} is a directory.")
    dir_path.mkdir(parents=True, exist_ok=True)

    env_text = f"""
    # Environment variables for {APP_NAME}
    # Load order is:
    # 1. f"{_app_dir}/.env",
    # 2. f"{_app_dir}/.secrets.env",
    # 3. <current working directory>.env
    # 4. <current working directory>.secrets.env
    # 5. Environment variables

    # The last value loaded will be used.

    # Example .env file:

    # {_app_env_prefix}APP_DIR={_app_dir}
    # {_app_env_prefix}LOG_DIR={_app_dir}/logs
    # {_app_env_prefix}DATA_DIR={_app_dir}/data
    # {_app_env_prefix}SCHEMA_DIR={_app_dir}/schema
    # {_app_env_prefix}CACHE_DIR={_app_dir}/cache
    # {_app_env_prefix}TEMP_DIR={_app_dir}/temp


    # For convenience, secrets can be loaded from .env file, or a separate .secrets.env
    # {_app_env_prefix}APP_SECRET=your_app_secret_here
    # {_app_env_prefix}CLIENT_SECRET=your_client_secret_here



    # File generated at {Instant.now().format_common_iso()}\n
    """
    env_path.write_text(env_text)
