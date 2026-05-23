from dataclasses import dataclass, field
from typing import TypedDict


@dataclass(slots=True, frozen=True)
class EsiAppCredentials:
    """EVE application credentials.

    Field names match the JSON keys returned by the ESI app registration page.
    https://developers.eveonline.com/applications
    """

    name: str
    description: str
    clientId: str
    clientSecret: str
    callbackUrl: str
    scopes: list[str] = field(default_factory=list[str])


@dataclass(slots=True, frozen=True)
class AuthenticationRequestParams:
    redirect_url: str
    """URL to redirect the user to for authentication."""
    state: str
    """CSRF protection string to validate the callback."""
    code_verifier: str
    """Code verifier for PKCE."""
    code_challenge: str
    """Code challenge for PKCE."""


class OauthTokenTD(TypedDict):
    """OAuth2 token response structure."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class ValidatedTokenTD(TypedDict):
    """Represents a validated/decoded character token.

    This information is extracted from the JWT access token after it has been validated.

    The sub field contains the character ID in `CHARACTER:EVE:<character_id>` format,
    the azp field contains the client ID, and the name field contains the character name.
    """

    scp: str
    jti: str
    kid: str
    sub: str
    azp: str
    tenant: str
    tier: str
    region: str
    aud: list[str]
    name: str
    owner: str
    exp: int
    iat: int
    iss: str
