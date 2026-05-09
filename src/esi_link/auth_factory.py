from esi_link.esi_auth.auth_store import AuthStoreRoot
from esi_link.esi_auth.authentication_tool import AuthenticationTool
from esi_link.esi_auth.models import EsiAppCredentials
from esi_link.esi_auth.token_tool import TokenTool
from esi_link.settings import EsiLinkSettings


def create_token_tool(settings: EsiLinkSettings) -> TokenTool:
    """Factory function to create a TokenTool instance using the provided settings."""
    return TokenTool(
        jwks_client=settings.jwks_client,
        user_agent=settings.user_agent,
    )


def create_authentication_tool(settings: EsiLinkSettings) -> AuthenticationTool:
    """Factory function to create an AuthenticationTool instance using the provided settings and app credentials."""
    if not settings.auth_credentials_file.exists():
        raise FileNotFoundError(
            f"App credentials file not found at {settings.auth_credentials_file}"
        )
    store_text = settings.auth_credentials_file.read_text()
    store = AuthStoreRoot.model_validate_json(store_text).root
    app_credentials = store.app_credentials
    return AuthenticationTool(
        client_id=app_credentials.clientId,
        scopes=app_credentials.scopes,
        callback_url=app_credentials.callbackUrl,
    )
