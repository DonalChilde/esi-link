"""Settings for the ESI Link application."""

from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from whenever import Instant

from esi_link import DEFAULT_APP_DIR, __app_name__, __version__

_app_env_prefix = "PFMSOFT_ESI_LINK_"


@dataclass(slots=True)
class OauthSettings:
    audience: str
    metadata_endpoint: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    revocation_endpoint: str
    issuers: list[str]


# These settings are current as of 2026-03-04, and are not likely to change much.
# They are included here for convenience, but can also be fetched dynamically from the metadata endpoint if needed.
# The current settings can be found at https://login.eveonline.com/.well-known/oauth-authorization-server
DEFAULT_OAUTH_SETTINGS = OauthSettings(
    audience="EVE Online",
    metadata_endpoint="https://login.eveonline.com/.well-known/oauth-authorization-server",
    authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
    token_endpoint="https://login.eveonline.com/v2/oauth/token",
    jwks_uri="https://login.eveonline.com/oauth/jwks",
    revocation_endpoint="https://login.eveonline.com/v2/oauth/revoke",
    issuers=["https://login.eveonline.com"],
)


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
    # config_file: Path = Field(
    #     default=DEFAULT_APP_DIR / "esi_link_config.json",
    #     description="The configuration file for ESI Link.",
    # )
    esi_schema_url: str = Field(
        default="https://esi.evetech.net/meta/openapi.json",
        description="The URL to download the ESI schema from.",
    )
    schema_store_path: Path = Field(
        default=DEFAULT_APP_DIR / "schema-store.json",
        description="The path to the store of indexed ESI schema files.",
    )
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
    auth_connection_string: str = Field(
        default=f"esi-auth-file:{DEFAULT_APP_DIR.resolve()}/esi-auth/esi-auth-store.json",
        description="The connection string for esi-auth integration.",
    )
    """Connection string for esi-auth integration."""
    auth_app_dir: Path = Field(
        default=DEFAULT_APP_DIR / "esi-auth",
        description="The application directory for esi-auth integration.",
    )
    """The application directory for esi-auth integration."""
    auth_server_timeout: int = Field(
        default=300,
        description="Timeout (in seconds) for the local auth server used by esi-auth.",
        ge=1,
        le=300,  # Max 5 minutes
    )
    """Timeout (in seconds) for the local auth server used by esi-auth."""

    # def auth_connection_string(self) -> str:
    #     """Get the auth connection string for esi-auth integration."""
    #     env_var_name = f"PFMSOFT_ESI_AUTH_AUTH_CONNECTION_STRING"
    #     # GET from environment variable if set
    #     return getenv(env_var_name, "")

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
    environ["PFMSOFT_ESI_AUTH_APP_DIR"] = str(settings.auth_app_dir.resolve())
    environ["PFMSOFT_ESI_AUTH_CONNECTION_STRING"] = settings.auth_connection_string
    environ["PFMSOFT_ESI_AUTH_AUTH_SERVER_TIMEOUT"] = str(settings.auth_server_timeout)

    # Ensure application directories exist
    settings.app_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_directory.mkdir(parents=True, exist_ok=True)
    settings.diskcache_directory.mkdir(parents=True, exist_ok=True)
    settings.json_cache_directory.mkdir(parents=True, exist_ok=True)
    settings.auth_app_dir.mkdir(parents=True, exist_ok=True)
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
