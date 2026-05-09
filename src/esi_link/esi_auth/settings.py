# """Settings for the ESI Auth application."""

# from dataclasses import dataclass
# from pathlib import Path

# import typer
# from pydantic import Field
# from pydantic_settings import BaseSettings, SettingsConfigDict

# from esi_link.esi_auth import (
#     AUDIENCE,
#     ISSUER,
#     OAUTH_METADATA_URL,
#     __app_name__,
#     __url__,
#     __version__,
# )

# _app_env_prefix = "PFMSOFT_ESI_AUTH_"
# USER_AGENT = f"{__app_name__}/{__version__} (+{__url__})"
# NAMESPACE = "pfmsoft"
# APPLICATION_NAME = "esi-auth"
# DEFAULT_APP_DIR = Path(typer.get_app_dir(f"{NAMESPACE}-{APPLICATION_NAME}"))
# # TODO Consistent location for the above constants between projects.


# @dataclass(slots=True)
# class EsiAuthSettings:
#     """Settings for the ESI Auth application."""

#     application_directory: Path = DEFAULT_APP_DIR
#     logging_directory: Path = DEFAULT_APP_DIR / "logs"
#     application_credentials: Path = DEFAULT_APP_DIR / "credentials.json"
#     tokens_directory: Path = DEFAULT_APP_DIR / "tokens"
#     token_refresh_threshold_seconds: int = (
#         300  # Refresh tokens if they expire within the next 5 minutes
#     )
#     cached_oauth_settings_file: Path = DEFAULT_APP_DIR / "oauth_settings.json"
#     cached_metadata_max_age: int = 86400  # Max age in seconds for cached OAuth metadata
#     oauth_metadata_url: str = OAUTH_METADATA_URL
#     auth_server_timeout: int = 300  # Max 5 minutes
#     audience: str = AUDIENCE
#     issuer: str = ISSUER
#     user_agent: str = USER_AGENT


# class EsiAuthSettingsPydantic(BaseSettings):
#     """Settings for the ESI Auth application."""

#     application_directory: Path = Field(
#         default=DEFAULT_APP_DIR, description="Directory for application data."
#     )
#     logging_directory: Path = Field(
#         default=DEFAULT_APP_DIR / "logs", description="Directory for log files."
#     )
#     application_credentials: Path = Field(
#         default=DEFAULT_APP_DIR / "credentials.json",
#         description="Path to the application credential JSON file.",
#     )
#     tokens_directory: Path = Field(
#         default=DEFAULT_APP_DIR / "tokens",
#         description="Directory for the application ESI token JSON files.",
#     )
#     cached_oauth_settings_file: Path = Field(
#         default=DEFAULT_APP_DIR / "oauth_settings.json",
#         description="Path to the cached OAuth settings JSON file.",
#     )
#     cached_metadata_max_age: int = Field(
#         default=86400,
#         description="Maximum age in seconds for cached OAuth metadata before it is considered stale and needs to be refreshed.",
#         ge=1,
#     )
#     oauth_metadata_url: str = Field(
#         default=OAUTH_METADATA_URL,
#         description="URL to fetch OAuth metadata from the ESI auth server.",
#     )
#     audience: str = Field(
#         default=AUDIENCE,
#         description="The audience to use for ESI Auth tokens.",
#     )
#     issuer: str = Field(
#         default=ISSUER,
#         description="The issuer to use for ESI Auth tokens.",
#     )
#     auth_server_timeout: int = Field(
#         default=300,
#         description="Timeout in seconds for the auth server to respond.",
#         ge=1,
#         le=300,  # Max 5 minutes
#     )
#     model_config = SettingsConfigDict(
#         env_prefix=_app_env_prefix,
#         env_file=(f"{DEFAULT_APP_DIR.resolve()}/.esi-auth.env", ".esi-auth.env"),
#         env_file_encoding="utf-8",
#     )


# # @dataclass(slots=True)
# # class OauthSettings:
# #     audience: str
# #     metadata_endpoint: str
# #     authorization_endpoint: str
# #     token_endpoint: str
# #     jwks_uri: str
# #     revocation_endpoint: str
# #     issuers: list[str]


# # # These settings are current as of 2026-03-04, and are not likely to change much.
# # # They are included here for convenience, but can also be fetched dynamically from the metadata endpoint if needed.
# # # The current settings can be found at https://login.eveonline.com/.well-known/oauth-authorization-server
# # DEFAULT_OAUTH_SETTINGS = OauthSettings(
# #     audience="EVE Online",
# #     metadata_endpoint="https://login.eveonline.com/.well-known/oauth-authorization-server",
# #     authorization_endpoint="https://login.eveonline.com/v2/oauth/authorize",
# #     token_endpoint="https://login.eveonline.com/v2/oauth/token",
# #     jwks_uri="https://login.eveonline.com/oauth/jwks",
# #     revocation_endpoint="https://login.eveonline.com/v2/oauth/revoke",
# #     issuers=["https://login.eveonline.com"],
# # )


# # # TODO
# # class EsiAuthSettings(BaseSettings):
# #     """Settings for the ESI Auth application."""

# #     app_dir: Path = Field(
# #         default=DEFAULT_APP_DIR, description="Directory for application data."
# #     )
# #     log_dir: Path = Field(
# #         default=DEFAULT_APP_DIR / "logs", description="Directory for log files."
# #     )
# #     app_credentials_file: Path = Field(
# #         default=DEFAULT_APP_DIR / "credentials.json",
# #         description="Path to the application credential JSON file.",
# #     )
# #     tokens_dir: Path = Field(
# #         default=DEFAULT_APP_DIR / "tokens",
# #         description="Directory for the application ESI token JSON files.",
# #     )
# #     oauth_settings_file: Path = Field(
# #         default=DEFAULT_APP_DIR / "oauth_settings.json",
# #         description="Path to the OAuth settings JSON file.",
# #     )
# #     oauth_settings_url: str = Field(
# #         default="https://login.eveonline.com/.well-known/oauth-authorization-server",
# #         description="URL to fetch OAuth settings from the ESI auth server.",
# #     )
# #     auth_server_timeout: int = Field(
# #         default=300,
# #         description="Timeout in seconds for the auth server to respond.",
# #         ge=1,
# #         le=300,  # Max 5 minutes
# #     )

# #     model_config = SettingsConfigDict(
# #         env_prefix=_app_env_prefix,
# #         env_file=(f"{DEFAULT_APP_DIR.resolve()}/.esi-auth.env", ".esi-auth.env"),
# #         env_file_encoding="utf-8",
# #     )


# def get_settings() -> EsiAuthSettings:
#     """Get the application settings, ensuring that necessary directories exist."""
#     pydantic_settings = EsiAuthSettingsPydantic()
#     settings = EsiAuthSettings(
#         application_directory=pydantic_settings.application_directory,
#         logging_directory=pydantic_settings.logging_directory,
#         application_credentials=pydantic_settings.application_credentials,
#         tokens_directory=pydantic_settings.tokens_directory,
#         cached_oauth_settings_file=pydantic_settings.cached_oauth_settings_file,
#         oauth_metadata_url=pydantic_settings.oauth_metadata_url,
#         auth_server_timeout=pydantic_settings.auth_server_timeout,
#     )

#     # Ensure that the necessary directories exist
#     settings.application_directory.mkdir(parents=True, exist_ok=True)
#     settings.logging_directory.mkdir(parents=True, exist_ok=True)
#     settings.application_credentials.parent.mkdir(parents=True, exist_ok=True)
#     settings.tokens_directory.mkdir(parents=True, exist_ok=True)
#     return settings
