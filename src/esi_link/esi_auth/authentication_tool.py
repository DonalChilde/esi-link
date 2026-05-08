"""AuthenticationTool for ESI authorization codes."""

import asyncio
import logging
from typing import Any
from urllib.parse import urlencode, urlparse

from aiohttp import web

from esi_link.esi_auth.helpers.code_challenge import (
    generate_code_challenge_and_verifier,
)
from esi_link.esi_auth.helpers.secure_random_string import generate_secure_random_string
from esi_link.esi_auth.models import (
    AuthenticationRequestParams,
)
from esi_link.esi_auth.oauth_metadata import (
    AUTHORIZATION_ENDPOINT,
)

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Exception raised during authentication process.

    This exception is raised when authentication fails or encounters
    an error during the OAuth flow.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the authentication error."""
        super().__init__(*args, **kwargs)


class AuthenticationTool:
    """Tool for ESI authorization codes.

    This tool provides methods to aquire ESI authorization codes through the OAuth2 authorization code flow with PKCE.

    These codes can then be exchanged for access and refresh tokens to authenticate API requests on behalf of EVE characters.

    The authentication flow typically involves:
    1. Generating a URL for the user to visit to authorize the application.
    2. Running a temporary server to receive the OAuth callback and extract the authorization code.
    3. Returning the authorization code for further processing (e.g., exchanging for tokens).

    Example usage:
    ```python
    auth_tool = AuthenticationTool(
        client_id="your_client_id",
        scopes=["scope1", "scope2"],
        callback_url="http://localhost:8000/callback",
    )
    auth_params = auth_tool.generate_request_params()
    print(f"Please visit the following URL to authenticate: {auth_params.redirect_url}")
    authorization_code = asyncio.run(auth_tool.request_authentication_code(auth_params))
    print(f"Received authorization code: {authorization_code}")
    ```
    See `TokenTool` for exchanging the authorization code for Oauth tokens and `CharacterTokens`.
    """

    def __init__(
        self,
        client_id: str,
        scopes: list[str],
        callback_url: str,
        authorization_endpoint: str = AUTHORIZATION_ENDPOINT,
    ):
        """Initialize the AuthenticationTool.

        Args:
            client_id: The client ID of the ESI application.
            scopes: The list of scopes to request during authentication.
            callback_url: The URL to redirect the user to after authentication.
            authorization_endpoint: The OAuth authorization endpoint URL.
        """
        self.callback_url = callback_url
        self.client_id = client_id
        self.scopes = scopes
        self.authorization_endpoint = authorization_endpoint

    def generate_request_params(self) -> AuthenticationRequestParams:
        """Generate the request parameters for the authentication request."""
        code_challenge, code_verifier = generate_code_challenge_and_verifier()
        state = generate_secure_random_string(16)
        return AuthenticationRequestParams(
            redirect_url=generate_url(
                code_challenge=code_challenge,
                client_id=self.client_id,
                callback_url=self.callback_url,
                authorization_endpoint=self.authorization_endpoint,
                scopes=self.scopes,
                state=state,
            ),
            state=state,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
        )

    async def request_authentication_code(
        self, auth_params: AuthenticationRequestParams
    ) -> str:
        """Run the authentication flow and return the authorization code."""
        authentication_code = await self._run_callback_server(
            expected_state=auth_params.state
        )
        return authentication_code

    async def _run_callback_server(
        self, expected_state: str, timeout: int = 300
    ) -> str:
        """Run a temporary server to receive the OAuth callback and return the OAuth token.

        This method should be implemented by subclasses to provide the actual logic for running the callback server.
        """
        authorization_code = None
        error_message = None

        async def callback_handler(request: web.Request) -> web.Response:
            nonlocal authorization_code, error_message

            # Check for error in callback
            if "error" in request.query:
                error_message = request.query.get(
                    "error_description", request.query["error"]
                )
                return web.Response(
                    text="<h1>Authentication Failed</h1>"
                    f"<p>Error: {error_message}</p>"
                    "<p>You can close this window.</p>",
                    content_type="text/html",
                )

            # Validate state parameter
            received_state = request.query.get("state")
            if received_state != expected_state:
                error_message = "Invalid state parameter (possible CSRF attack)"
                return web.Response(
                    text="<h1>Authentication Failed</h1>"
                    "<p>Security validation failed. Please try again.</p>"
                    "<p>You can close this window.</p>",
                    content_type="text/html",
                )

            # Get authorization code
            logger.info(f"Received OAuth callback")
            authorization_code = request.query.get("code")
            if not authorization_code:
                error_message = "No authorization code received"
                return web.Response(
                    text="<h1>Authentication Failed</h1>"
                    "<p>No authorization code received.</p>"
                    "<p>You can close this window.</p>",
                    content_type="text/html",
                )

            return web.Response(
                text="<h1>Authentication Successful</h1>"
                "<p>You can now close this window and return to the application.</p>",
                content_type="text/html",
            )

        # Create and start the server
        app = web.Application()
        parsed_url = urlparse(self.callback_url)
        app.router.add_get(parsed_url.path, callback_handler)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, parsed_url.hostname, parsed_url.port)

        try:
            await site.start()
            logger.info(
                f"Callback server started on {self.callback_url}, waiting for authentication response..."
            )

            # Wait for callback or timeout
            for _ in range(timeout):
                if authorization_code or error_message:
                    break
                await asyncio.sleep(1)

            if error_message:
                raise AuthenticationError(f"OAuth callback error: {error_message}")

            if not authorization_code:
                raise AuthenticationError("Timeout waiting for OAuth callback")

            return authorization_code

        finally:
            await runner.cleanup()
            logger.debug("Callback server stopped")


def generate_state_string() -> str:
    """Generate a secure random string to use as the state parameter for CSRF protection."""
    return generate_secure_random_string(16)


def generate_url(
    code_challenge: str,
    client_id: str,
    callback_url: str,
    authorization_endpoint: str,
    scopes: list[str],
    state: str,
    code_challenge_method: str = "S256",
) -> str:
    """Generate the URL.

    The URL for the user to visit to authorize the application.
    """
    query_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": callback_url,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    query_string = urlencode(query_params)
    return f"{authorization_endpoint}?{query_string}"
