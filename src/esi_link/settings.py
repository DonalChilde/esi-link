"""Settings for the ESI Link application."""

from os import getenv
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from whenever import Instant

from esi_link import DEFAULT_APP_DIR

_app_env_prefix = "PFMSOFT_ESI_LINK_"


class EsiLinkSettings(BaseSettings):
    """Settings for the ESI Link application."""

    app_dir: Path = Field(
        default=DEFAULT_APP_DIR,
        description="The application directory for ESI Link.",
    )
    log_dir: Path = Field(
        default=DEFAULT_APP_DIR / "logs",
        description="The log directory for ESI Link.",
    )
    config_file: Path = Field(
        default=DEFAULT_APP_DIR / "esi_link_config.json",
        description="The configuration file for ESI Link.",
    )
    esi_schema_url: str = Field(
        default="https://esi.evetech.net/meta/openapi.json",
        description="The URL to download the ESI schema from.",
    )
    esi_schema_path: Path = Field(
        default=DEFAULT_APP_DIR / "esi_schema.json",
        description="The path to the ESI schema file.",
    )
    cache_connection_string: str = Field(
        default=f"esi-link-file:{DEFAULT_APP_DIR.resolve()}/esi-link-cache.json",
        description="The connection string for ESI Link cache.",
    )
    """Connection string for the cache backend.

    Format: [cache_type]://[path_or_connection_info]

    Examples:
        File-based cache: esi-link-json:///path/to/cache/dir
        In-memory cache: esi-link-memory://"""

    connection_period: int = Field(
        default=60,
        description="Period (in seconds) for ESI Link connection rate limiting.",
    )
    """Period (in seconds) for ESI Link connection rate limiting."""
    connection_max_rate: int = Field(
        default=100,
        description="Maximum number of requests per period for ESI Link connections.",
    )
    """Maximum number of concurrent connections to ESI per period."""

    def auth_connection_string(self) -> str:
        """Get the auth connection string for esi-auth integration."""
        env_var_name = f"PFMSOFT_ESI_AUTH_AUTH_CONNECTION_STRING"
        # GET from environment variable if set
        return getenv(env_var_name, "")

    model_config = SettingsConfigDict(
        env_file=(
            f"{DEFAULT_APP_DIR}/.esi-link.env",
            ".esi-link.env",
        ),
        env_prefix=_app_env_prefix,
    )


def get_settings() -> EsiLinkSettings:
    """Get the ESI Link settings."""
    return EsiLinkSettings()


def env_example() -> str:
    """Get an example of environment variables for ESI Link settings."""
    # TODO include instructions on how to set up esi-auth env vars too
    env_example_str = f"""# ESI Link Environment Variables
    # File generated at {Instant.now().format_iso()}\n

    # Env variable load order:
    # 1. .esi-link.env files in application directory
    # 2. .esi-link.env files in current working directory
    # 3. System environment variables

    # Uncomment and set the following environment variables to override default settings.

    # Application Directory
    #{_app_env_prefix}APP_DIR="{DEFAULT_APP_DIR.resolve()}"

    # Log Directory
    #{_app_env_prefix}LOG_DIR="${{{_app_env_prefix}APP_DIR}}/logs"

    # Configuration File
    #{_app_env_prefix}CONFIG_FILE="${{{_app_env_prefix}APP_DIR}}/esi_link_config.json"

    # Esi Schema Url
    #{_app_env_prefix}ESI_SCHEMA_URL="https://esi.evetech.net/meta/openapi.json"

    # Cache Connection String
    #{_app_env_prefix}CACHE_CONNECTION_STRING="esi-link-cache-file:${{{_app_env_prefix}APP_DIR}}/esi-link-cache.json"

    # Connection Rate Limiting
    #{_app_env_prefix}CONNECTION_PERIOD=60
    #{_app_env_prefix}CONNECTION_MAX_RATE=100
    """
    return env_example_str
