# """An implementation of the AuthProviderProtocol."""

# from esi_link.esi_auth.models import CharacterAuth
# from esi_link.esi_auth.protocols import (
#     AuthProviderProtocol,
#     CharacterTokenManagerProtocol,
# )


# class AuthProvider(AuthProviderProtocol):
#     """AuthProvider implementation."""

#     def __init__(self, token_manager: CharacterTokenManagerProtocol):
#         self.token_manager = token_manager

#     async def character_auth(
#         self, character_id: int, min_seconds: int = 300
#     ) -> CharacterAuth:
#         """Return the authentication information for the given character ID.

#         Args:
#             character_id: The ID of the character for which to retrieve the authentication information.
#             min_seconds: The minimum number of seconds before a token expires to
#                 trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).

#         Returns:
#             The authentication information for the given character ID.
#         """
#         character_token = await self.token_manager.get_token(
#             character_id, min_seconds=min_seconds
#         )
#         auth = CharacterAuth(
#             character_id=character_token.character_id,
#             character_name=character_token.character_name,
#             auth_headers={
#                 "Authorization": f"Bearer {character_token.oauth_token.access_token}"
#             },
#             expires_at=character_token.expires,
#         )
#         return auth

#     async def available_characters(self, min_seconds: int = 300) -> list[int]:
#         """Return a list of character IDs for which authentication information is available.

#         This method returns the character IDs for all characters that have valid authentication
#         information available. If min_seconds is set to a non-negative value, it will
#         also refresh any tokens that are about to expire within that time frame before
#         returning the character IDs.

#         A bulk refresh is used for efficiency when multiple tokens need to be refreshed,
#         as it allows for concurrent refreshes, depending on implementation.

#         Args:
#             min_seconds: The minimum number of seconds before a token expires to
#                 trigger a refresh. -1 to disable refresh. Default is 300 (5 minutes).
#         """
#         tokens = await self.token_manager.list_tokens(min_seconds=min_seconds)
#         return [x.character_id for x in tokens]
