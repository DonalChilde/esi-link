# TODO implement the AuthProviderProtocol, a front end to esi-auth.


from esi_link.v2.models import AuthProviderProtocol


class DummyAuthProvider(AuthProviderProtocol):
    """A dummy auth provider that returns fixed auth parameters for testing."""

    def get_auth_token(
        self, character_id: int, client_alias: str | None = None
    ) -> dict[str, str | int]:
        """Return dummy auth parameters for the given client alias."""
        return {
            "client_alias": client_alias if client_alias else "default",
            "access_token": "dummy_access_token",
            "refresh_token": "dummy_refresh_token",
            "expires_in": 3600,
        }

    def get_auth_headers(
        self, character_id: int, client_alias: str | None = None
    ) -> dict[str, str]:
        """Return dummy auth headers for the given character ID and client alias."""
        return {
            "Authorization": f"Bearer dummy_access_token_for_character_{character_id}_alias_{client_alias}"
        }
