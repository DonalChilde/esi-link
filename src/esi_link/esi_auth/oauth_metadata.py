"""Oauth metadata settings and functions.

Defines constants and functions related to EVE Online's OAuth 2.0 implementation.

The constants can be used as default argument for functions that need to fetch or use
OAuth metadata. Actors calling those functions are resonsible for supplying up to date
metadata if required.
"""

import json
import logging
from pathlib import Path
from typing import Any

import aiohttp
from whenever import Instant

from esi_link.esi_auth.models import CachedMetadata

logger = logging.getLogger(__name__)

AUDIENCE = "EVE Online"
METADATA_ENDPOINT = "https://login.eveonline.com/.well-known/oauth-authorization-server"
AUTHORIZATION_ENDPOINT = "https://login.eveonline.com/v2/oauth/authorize"
TOKEN_ENDPOINT = "https://login.eveonline.com/v2/oauth/token"
JWKS_URI = "https://login.eveonline.com/oauth/jwks"
REVOCATION_ENDPOINT = "https://login.eveonline.com/v2/oauth/revoke"
ISSUER = "https://login.eveonline.com"
TOKEN_ALGORITHM = "RS256"


STATIC_METADATA: dict[str, Any] = {
    "issuer": "https://login.eveonline.com",
    "authorization_endpoint": "https://login.eveonline.com/v2/oauth/authorize",
    "token_endpoint": "https://login.eveonline.com/v2/oauth/token",
    "userinfo_endpoint": "https://login.eveonline.com/v2/oauth/verify",
    "response_types_supported": ["code", "token"],
    "jwks_uri": "https://login.eveonline.com/oauth/jwks",
    "revocation_endpoint": "https://login.eveonline.com/v2/oauth/revoke",
    "subject_types_supported": ["public"],
    "revocation_endpoint_auth_methods_supported": [
        "client_secret_basic",
        "client_secret_post",
        "client_secret_jwt",
    ],
    "token_endpoint_auth_methods_supported": [
        "client_secret_basic",
        "client_secret_post",
        "client_secret_jwt",
    ],
    "id_token_signing_alg_values_supported": ["HS256"],
    "token_endpoint_auth_signing_alg_values_supported": ["HS256"],
    "code_challenge_methods_supported": ["S256"],
}
"""From the EVE Online OAuth metadata endpoint as of 2026-03-12."""

STATIC_JWKS: dict[str, Any] = {
    "keys": [
        {
            "alg": "RS256",
            "e": "AQAB",
            "kid": "JWT-Signature-Key",
            "kty": "RSA",
            "n": "nehPQ7FQ1YK-leKyIg-aACZaT-DbTL5V1XpXghtLX_bEC-fwxhdE_4yQKDF6cA-V4c-5kh8wMZbfYw5xxgM9DynhMkVrmQFyYB3QMZwydr922UWs3kLz-nO6vi0ldCn-ffM9odUPRHv9UbhM5bB4SZtCrpr9hWQgJ3FjzWO2KosGQ8acLxLtDQfU_lq0OGzoj_oWwUKaN_OVfu80zGTH7mxVeGMJqWXABKd52ByvYZn3wL_hG60DfDWGV_xfLlHMt_WoKZmrXT4V3BCBmbitJ6lda3oNdNeHUh486iqaL43bMR2K4TzrspGMRUYXcudUQ9TycBQBrUlT85NRY9TeOw",
            "use": "sig",
        },
        {
            "alg": "ES256",
            "crv": "P-256",
            "kid": "8878a23f-2489-4045-989e-4d2f3ec1ae1a",
            "kty": "EC",
            "use": "sig",
            "x": "PatzB2HJzZOzmqQyYpQYqn3SAXoVYWrZKmMgJnfK94I",
            "y": "qDb1kUd13fRTN2UNmcgSoQoyqeF_C1MsFlY_a87csnY",
        },
    ],
    "SkipUnresolvedJsonWebKeys": True,
}
"""From the EVE Online OAuth metadata jwkd_uri endpoint as of 2026-03-12."""


def _load_cached_oauth_metadata(file_path: Path) -> CachedMetadata:
    """Load the OAuth metadata from a JSON file."""
    with file_path.open() as f:
        data = json.load(f)
    return CachedMetadata(**data)


async def oauth_metadata_cache(
    file_path: Path, *, max_age: int = 86400, url: str = METADATA_ENDPOINT
) -> CachedMetadata:
    """Load the OAuth metadata from a JSON file, or fetch it if the file does not exist."""
    if file_path.exists():
        cached_metadata = _load_cached_oauth_metadata(file_path)
        seconds_remaining = (
            cached_metadata["fetched_at"] + max_age - Instant.now().timestamp()
        )
        if seconds_remaining > 0:
            logger.info(
                f"Loaded OAuth metadata from cache. Metadata is {max_age - seconds_remaining:.0f} "
                f"seconds old and will expire in {seconds_remaining:.0f} seconds."
            )
            return cached_metadata
        else:
            logger.info(
                f"Cached OAuth metadata is expired. Metadata is {max_age - seconds_remaining:.0f} "
                f"seconds old and expired {abs(seconds_remaining):.0f} seconds ago. Fetching new metadata."
            )
    logger.info("No cached OAuth metadata found. Fetching new metadata from %s.", url)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            metadata = await response.json()
    cached_metadata = CachedMetadata(
        metadata=metadata, fetched_at=Instant.now().timestamp()
    )
    with file_path.open("w") as f:
        json.dump(cached_metadata, f, indent=2)
    logger.info(
        "Fetched and cached new OAuth metadata from %s, and saved it to %s.",
        url,
        file_path,
    )
    return cached_metadata
