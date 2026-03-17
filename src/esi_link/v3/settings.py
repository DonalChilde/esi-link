"""Settings for the ESI Link application."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from whenever import Instant

from esi_link import DEFAULT_APP_DIR, __app_name__, __version__

_app_env_prefix = "PFMSOFT_ESI_LINK_"

ESI_SCHEMA_URL = "https://esi.evetech.net/meta/openapi.json"
"""The URL to download the ESI schema from."""
ESI_SCHEMA_CHANGELOG_URL = "https://esi.evetech.net/meta/changelog.json"
"""The URL to download the ESI schema changelog from."""


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

    # -----------------------------------------------------------------------------------
    # Schema settings
    # -----------------------------------------------------------------------------------

    esi_schema_url: str = Field(
        default=ESI_SCHEMA_URL,
        description="The URL to download the ESI schema from.",
    )
    esi_schema_changelog_url: str = Field(
        default=ESI_SCHEMA_CHANGELOG_URL,
        description="The URL to download the ESI schema changelog from.",
    )
    schema_store_dir: Path = Field(
        default=DEFAULT_APP_DIR / "schema-store/",
        description="The path to the store of ESI schema files.",
    )

    # -----------------------------------------------------------------------------------
    # Cache settings
    # -----------------------------------------------------------------------------------

    cache_directory: Path = Field(
        default=DEFAULT_APP_DIR / "cache",
        description="The directory for ESI Link cache files.",
    )
    cache_type: Literal["diskcache", "json"] = Field(
        default="json",
        description="The type of cache to use for ESI Link.",
    )
    diskcache_directory: Path = Field(
        default=DEFAULT_APP_DIR / "cache" / "disk_cache",
        description="The directory for ESI Link diskcache files.",
    )
    json_cache_directory: Path = Field(
        default=DEFAULT_APP_DIR / "cache" / "json_cache",
        description="The directory for ESI Link JSON cache files.",
    )

    # -----------------------------------------------------------------------------------
    # Rate limiting settings
    # -----------------------------------------------------------------------------------

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

    # -----------------------------------------------------------------------------------
    # ESI Auth settings
    # -----------------------------------------------------------------------------------

    app_credentials_file: Path = Field(
        default=DEFAULT_APP_DIR / "esi-auth" / "credentials.json",
        description="Path to the application credential JSON file.",
    )
    """Path to the application credential JSON file."""
    tokens_dir: Path = Field(
        default=DEFAULT_APP_DIR / "esi-auth" / "tokens",
        description="Directory for the application ESI token JSON files.",
    )
    """Directory for the application ESI token JSON files."""
    oauth_metadata_url: str = Field(
        default="https://login.eveonline.com/.well-known/oauth-authorization-server",
        description="URL to fetch OAuth metadata from the ESI auth server.",
    )
    """URL to fetch OAuth metadata from the ESI auth server."""
    cached_oauth_metadata_file: Path = Field(
        default=DEFAULT_APP_DIR / "esi-auth" / "oauth_metadata.json",
        description="Path to the cached OAuth metadata JSON file.",
    )
    """Path to the cached OAuth metadata JSON file."""
    cached_metadata_max_age: int = Field(
        default=86400,
        description="Maximum age (in seconds) for cached OAuth metadata before it is considered expired.",
    )
    """Maximum age (in seconds) for cached OAuth metadata before it is considered expired."""

    auth_server_timeout: int = Field(
        default=300,
        description="Timeout (in seconds) for the local auth server used by esi-auth.",
        ge=1,
        le=300,  # Max 5 minutes
    )
    """Timeout (in seconds) for the local auth server used by esi-auth."""
    audience: str = Field(
        default="EVE Online",
        description="The audience to use for ESI Auth tokens.",
    )
    """The audience to use for ESI Auth tokens."""
    issuer: str = Field(
        default="https://login.eveonline.com",
        description="The issuer to use for ESI Auth tokens.",
    )
    """The issuer to use for ESI Auth tokens."""

    model_config = SettingsConfigDict(
        env_file=(
            f"{DEFAULT_APP_DIR}/.esi-link.env",
            ".esi-link.env",
        ),
        env_prefix=_app_env_prefix,
    )


def get_settings() -> EsiLinkSettings:
    """Get the ESI Link settings."""
    settings = EsiLinkSettings()

    # Ensure application directories exist
    settings.app_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_directory.mkdir(parents=True, exist_ok=True)
    settings.diskcache_directory.mkdir(parents=True, exist_ok=True)
    settings.json_cache_directory.mkdir(parents=True, exist_ok=True)
    settings.cached_oauth_metadata_file.parent.mkdir(parents=True, exist_ok=True)
    return settings


def env_example() -> str:
    """Get an example of environment variables for ESI Link settings."""
    # TODO include instructions on how to set up esi-auth env vars too
    env_example_str = f"""# ESI Link Environment Variables
    # File generated by {__app_name__}/{__version__} at {Instant.now().format_iso()}\n

    # Env variable load order, last loaded takes precedence:
    # 1. .esi-link.env files in application directory
    # 2. .esi-link.env files in current working directory
    # 3. System environment variables

    # Instructions:
    # - Uncomment and set the environment variables to override default settings.
    # - a set of env files are created in the default application directory when you run
    #   `esi-link <some command>` for the first time.
    # - You can also create env files in the current working directory to customize these 
    #   variables persistently. See `esi-link example-env`--help` for more details.
    # - See the documentation for more details on each setting.
    # - Remember to also set up esi-auth environment variables if you plan to use authentication.
    #   - You will normally change the esi-auth app_dir and auth_connection_string settings to
    #     point to the same application directory as esi-link, with a sub-directory of 'esi-auth'.
    #     - Example: PFMSOFT_ESI_AUTH_APP_DIR="{DEFAULT_APP_DIR.resolve()}/esi-auth"
    #     - Example: PFMSOFT_ESI_AUTH_AUTH_CONNECTION_STRING="esi-auth-file:{DEFAULT_APP_DIR.resolve()}/esi-auth/esi-auth-cache.json"
    #     If you do not set these, esi-auth will use its own default application directory.
    

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

    # ESI Auth settings
    #AUTH_APP_DIR="${{{_app_env_prefix}APP_DIR}}/esi-auth"
    #AUTH_CONNECTION_STRING="esi-auth-file:${{{_app_env_prefix}APP_DIR}}/esi-auth/esi-auth-store.json"
    #AUTH_SERVER_TIMEOUT=300
    """
    return env_example_str
