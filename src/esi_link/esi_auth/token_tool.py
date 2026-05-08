"""Tools for managing ESI Oauth tokens."""

import logging
from typing import Any

import aiohttp
import jwt
from jwt.jwks_client import PyJWKClient

from esi_link import USER_AGENT
from esi_link.esi_auth.models import CharacterToken, OauthToken
from esi_link.esi_auth.oauth_metadata import (
    AUDIENCE,
    ISSUER,
    REVOCATION_ENDPOINT,
    TOKEN_ALGORITHM,
    TOKEN_ENDPOINT,
)

logger = logging.getLogger(__name__)


class TokenValidationError(Exception):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Custom exception for token validation errors."""
        super().__init__(*args, **kwargs)


class NewTokenRequestError(Exception):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Custom exception for errors during new token requests."""
        super().__init__(*args, **kwargs)


class TokenRefreshError(Exception):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Custom exception for errors during token refresh."""
        super().__init__(*args, **kwargs)


class DecodeTokenError(Exception):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Custom exception for errors during token decoding."""
        super().__init__(*args, **kwargs)


class TokenTool:
    """Tool for managing ESI Oauth tokens."""

    def __init__(
        self,
        jwks_client: PyJWKClient,
        user_agent: str = USER_AGENT,
        audience: str = AUDIENCE,
        token_endpoint: str = TOKEN_ENDPOINT,
        revocation_endpoint: str = REVOCATION_ENDPOINT,
        issuer: str = ISSUER,
        token_alg: str = TOKEN_ALGORITHM,
    ):
        """Initialize the TokenTool with the given parameters.

        Args:
            jwks_client: The PyJWKClient instance to use for fetching signing keys.
            user_agent: The user agent to use for HTTP requests.
            audience: The expected audience for the tokens.
            token_endpoint: The OAuth token endpoint URL.
            revocation_endpoint: The OAuth token revocation endpoint URL.
            issuer: The expected issuer for the tokens.
            token_alg: The expected signing algorithm for the tokens.
        """
        self.jwks_client = jwks_client
        self.user_agent = user_agent
        self.token_alg = token_alg
        self.audience = audience
        self.issuer = issuer
        self.token_endpoint = token_endpoint
        self.revocation_endpoint = revocation_endpoint

    async def request_new_token(
        self,
        client_id: str,
        authorization_code: str,
        code_verifier: str,
        client_session: aiohttp.ClientSession,
    ) -> OauthToken:
        """Request a new OAuth token using the authorization code flow.

        Args:
            client_id: The client ID of the application.
            authorization_code: The authorization code received from the authorization server.
            code_verifier: The code verifier used in the PKCE flow.
            client_session: The aiohttp ClientSession to use for the request.

        Returns:
            An OauthToken instance containing the new token information.

        Raises:
            ValueError: If client_session is not initialized.
            NewTokenRequestError: If there is an error during the token request.
        """
        new_token = await request_new_token(
            client_id=client_id,
            authorization_code=authorization_code,
            code_verifier=code_verifier,
            client_session=client_session,
            token_endpoint=self.token_endpoint,
            user_agent=self.user_agent,
        )
        return OauthToken(**new_token)

    async def refresh_token(
        self,
        client_id: str,
        refresh_token_value: str,
        client_session: aiohttp.ClientSession,
    ) -> OauthToken:
        """Refresh an existing OAuth token.

        Args:
            client_id: The client ID of the application.
            refresh_token_value: The refresh token value to use for refreshing.
            client_session: The aiohttp ClientSession to use for the request.

        Returns:
            An OauthToken instance containing the refreshed token information.

        Raises:
            TokenRefreshError: If there is an error during the token refresh request.
            ValueError: If client_session is not initialized.
        """
        refreshed_token = await refresh_token(
            client_id=client_id,
            refresh_token_value=refresh_token_value,
            client_session=client_session,
            token_endpoint=self.token_endpoint,
            user_agent=self.user_agent,
        )
        return OauthToken(**refreshed_token)

    async def revoke_token(
        self,
        client_id: str,
        refresh_token_value: str,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Revoke an existing OAuth token.

        Args:
            client_id: The client ID of the application.
            refresh_token_value: The refresh token value to revoke.
            client_session: The aiohttp ClientSession to use for the request.

        Raises:
            TokenRefreshError: If there is an error during the token revocation request.
            ValueError: If client_session is not initialized.
        """
        await revoke_token(
            client_id=client_id,
            refresh_token_value=refresh_token_value,
            client_session=client_session,
            revocation_endpoint=self.revocation_endpoint,
            user_agent=self.user_agent,
        )

    def character_token_from_oauth_token(
        self, oauth_token: OauthToken
    ) -> CharacterToken:
        """Convert an OauthToken to a CharacterToken by decoding the access token.

        Args:
            oauth_token: The OauthToken to convert.

        Returns:
            A CharacterToken containing the character ID, character name, token creation
            time, token expiration time, and the original OauthToken.

        Raises:
            DecodeTokenError: If there is an error during token decoding or if the decoded token does
        """
        decoded = decode_token(
            access_token=oauth_token.access_token,
            token_alg=self.token_alg,
            audience=self.audience,
            issuer=self.issuer,
            jwks_client=self.jwks_client,
        )
        character_id = decoded["sub"].split(":")[-1]
        character_name = decoded["name"]
        return CharacterToken(
            character_id=int(character_id),
            character_name=character_name,
            created=decoded["iat"],
            expires=decoded["exp"],
            oauth_token=oauth_token,
        )


async def revoke_token(
    client_id: str,
    refresh_token_value: str,
    client_session: aiohttp.ClientSession,
    revocation_endpoint: str,
    user_agent: str,
) -> None:
    """Revoke an existing OAuth token.

    Args:
        client_id: The client ID of the application.
        refresh_token_value: The refresh token value to revoke.
        client_session: The aiohttp ClientSession to use for the request.
        revocation_endpoint: The OAuth token revocation endpoint URL.
        user_agent: The user agent to use for the HTTP request.

    Raises:
        TokenRefreshError: If there is an error during the token revocation request.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": user_agent,
    }
    payload: dict[str, str] = {
        "token": refresh_token_value,
        "token_type_hint": "refresh_token",
        "client_id": client_id,
    }

    response = await client_session.post(
        revocation_endpoint, headers=headers, data=payload
    )
    response.raise_for_status()
    if response.status == 200:
        logger.info("Token revoked successfully")


async def refresh_token(
    client_id: str,
    refresh_token_value: str,
    client_session: aiohttp.ClientSession,
    token_endpoint: str,
    user_agent: str,
) -> dict[str, Any]:
    """Refresh an existing OAuth token.

    Args:
        client_id: The client ID of the application.
        refresh_token_value: The refresh token value to use for refreshing.
        client_session: The aiohttp ClientSession to use for the request.
        token_endpoint: The OAuth token endpoint URL.
        user_agent: The user agent to use for the HTTP request.

    Raises:
        TokenRefreshError: If there is an error during the token refresh request.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": user_agent,
    }
    payload: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
        "client_id": client_id,
    }
    try:
        response = await client_session.post(
            token_endpoint, headers=headers, data=payload
        )
        response.raise_for_status()
        token = await response.json()
    except Exception as e:
        logger.exception(f"Error refreshing token: {e}")
        raise TokenRefreshError(f"Error refreshing token: {e}") from e
    return token


async def request_new_token(
    client_id: str,
    authorization_code: str,
    code_verifier: str,
    client_session: aiohttp.ClientSession,
    token_endpoint: str,
    user_agent: str,
) -> dict[str, Any]:
    """Request a new OAuth token using the authorization code flow.

    Args:
        client_id: The client ID of the application.
        authorization_code: The authorization code received from the authorization server.
        code_verifier: The code verifier used in the PKCE flow.
        client_session: The aiohttp ClientSession to use for the request.
        token_endpoint: The OAuth token endpoint URL.
        user_agent: The user agent to use for the HTTP request.

    Raises:
        NewTokenRequestError: If there is an error during the token request.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": user_agent,
    }
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    try:
        response = await client_session.post(
            token_endpoint, headers=headers, data=payload
        )
        response.raise_for_status()
        return await response.json()
    except Exception as e:
        logger.exception(f"Error requesting new token: {e}")
        raise NewTokenRequestError(f"Error requesting new token: {e}") from e


def decode_token(
    access_token: str,
    token_alg: str,
    audience: str,
    issuer: str,
    user_agent: str | None = None,
    jwks_uri: str | None = None,
    jwks_client: PyJWKClient | None = None,
) -> dict[str, Any]:
    """Decode and validate an OAuth access token.

    Args:
        access_token: The OAuth access token to decode.
        token_alg: The expected token signing algorithm.
        audience: The expected audience claim.
        issuer: The expected issuer claim.
        user_agent: The user agent to use for the HTTP request (if jwks_client is not provided).
        jwks_uri: The JWKS URI to fetch the signing keys (if jwks_client is not provided).
        jwks_client: The PyJWKClient instance to use for fetching signing keys.

    Raises:
        DecodeTokenError: If there is an error during token decoding.
    """
    if not jwks_client:
        if not jwks_uri:
            raise ValueError(
                "jwks_uri must be provided if jwks_client is not provided."
            )
        if not user_agent:
            raise ValueError(
                "user_agent must be provided if jwks_client is not provided."
            )
        jwks_client = PyJWKClient(jwks_uri, headers={"User-Agent": user_agent})
    unverified_header = jwt.get_unverified_header(access_token)
    if unverified_header.get("alg") != token_alg:
        logger.exception(
            f"Unexpected token alg: {unverified_header.get('alg')}, expected: {token_alg}"
        )
        raise DecodeTokenError(
            f"Unexpected token alg: {unverified_header.get('alg')}, expected: {token_alg}"
        )
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(access_token).key
        decoded_token = jwt.decode(
            jwt=access_token,
            key=signing_key,
            algorithms=[token_alg],
            audience=audience,
            issuer=issuer,
            options={"verify_aud": False, "verify_iss": False},
        )
    except Exception as e:
        logger.exception(f"Error decoding token: {e}")
        raise DecodeTokenError(f"Error decoding token: {e}") from e
    return decoded_token
