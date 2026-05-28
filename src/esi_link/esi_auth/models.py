"""Models for ESI Auth."""

from dataclasses import dataclass, field
from typing import TypedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, RootModel
from whenever import Instant

from esi_link.rewrite.response.models import Response
from esi_link.rewrite.runtime.models import RequestGroupMetrics


@dataclass(slots=True, frozen=True)
class CharacterAuth:
    """The return from the `AuthProviderProtocol.character_auth` method."""

    character_id: int
    character_name: str
    auth_headers: dict[str, str]
    expires_at: int


@dataclass(slots=True, frozen=True)
class OauthToken:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


@dataclass(slots=True, frozen=True)
class DecodedToken:
    pass


class OauthMetadata(TypedDict):
    """OAuth2 server metadata from well-known endpoint."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    response_types_supported: list[str]
    jwks_uri: str
    revocation_endpoint: str
    subject_types_supported: list[str]
    revocation_endpoint_auth_methods_supported: list[str]
    token_endpoint_auth_methods_supported: list[str]
    id_token_signing_alg_values_supported: list[str]
    token_endpoint_auth_signing_alg_values_supported: list[str]
    code_challenge_methods_supported: list[str]


class CachedMetadata(TypedDict):
    """Cached OAuth2 server metadata."""

    metadata: OauthMetadata
    fetched_at: int


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


EsiAppCredentialsRoot = RootModel[EsiAppCredentials]


@dataclass(slots=True, frozen=True)
class CharacterToken:
    character_id: int
    character_name: str
    created: int
    """Creation time as a UNIX timestamp."""
    expires: int
    """Expiration time as a UNIX timestamp."""
    oauth_token: OauthToken

    @property
    def expires_in(self) -> int:
        """Return the number of seconds until the token expires."""
        return self.expires - Instant.now().timestamp()

    @property
    def access_token(self) -> str:
        """Return the access token string."""
        return self.oauth_token.access_token

    @property
    def refresh_token(self) -> str:
        """Return the refresh token string."""
        return self.oauth_token.refresh_token

    @property
    def auth_headers(self) -> dict[str, str]:
        """Return the auth headers to use for authenticated requests to ESI."""
        return {"Authorization": f"Bearer {self.access_token}"}


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


@dataclass(slots=True, frozen=True)
class ValidatedToken:
    character_id: int
    character_name: str
    created_at: int
    expires_at: int


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseGroup:
    group_id: UUID
    description: str = ""
    responses: dict[UUID, Response] = field(default_factory=dict[UUID, Response])
    metrics: RequestGroupMetrics = field(default_factory=RequestGroupMetrics)


# class AppCredentials(BaseModel):
#     alias: str
#     credentials: EveAppCredentials

#     model_config = ConfigDict(frozen=True)
