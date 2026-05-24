"""Settings for the Esi Link application."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from jwt.jwks_client import PyJWKClient
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from whenever import Instant

from esi_link.rewrite import DEFAULT_APP_DIR, USER_AGENT, __app_name__, __version__

_app_env_prefix = "PFMSOFT_ESI_LINK_"

OAUTH_METADATA_URL = (
    "https://login.eveonline.com/.well-known/oauth-authorization-server"
)
"""URL to fetch OAuth metadata from the ESI auth server."""
ESI_SCHEMA_URL = "https://esi.evetech.net/meta/openapi.json"
"""URL to fetch ESI OpenAPI schema.

Example: 
    https://esi.evetech.net/meta/openapi.json?compatibility_date=2026-05-19

The schemas are versioned by compatibility date. If no compatibility date is provided, the 
schema downloaded will be the OLDEST schema available, which is not likely what is desired.

Provide a date in the past to get the latest schema. future dates are not allowed.

The API changes at 11:00 UTC, so use `now() minus 11 hours` as an iso date to get the latest schema.
"""


@dataclass(slots=True)
class EsiLinkSettings:
    """Settings for the ESI Link application."""


class EsiLinkSettingsPydantic(BaseSettings):
    """Settings for the ESI Link application.

    This settings class uses Pydantic for validation and loading from environment variables.
    It includes properties for various directories and configuration options used by ESI Link,
    such as schema URLs, cache settings, rate limiting settings, and ESI Auth settings.
    The settings can be overridden by environment variables with the prefix "PFMSOFT_ESI_LINK_"
    or by .esi-link.env files in the application directory or current working directory.

    This is NOT the class used to configure the app, Its responsibility is loading settings
    from environment variables and providing defaults. The EsiLinkSettings dataclass is
    the main settings class used for the app, and it can be constructed from this Pydantic
    settings class. This separation allows us to use Pydantic's powerful settings management
    features while keeping the main settings class simple and focused on the application's
    needs.
    """
