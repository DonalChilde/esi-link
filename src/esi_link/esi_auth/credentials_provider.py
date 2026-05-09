# """Credentials provider implementation for ESI Link."""

# import logging
# from pathlib import Path

# from esi_link.esi_auth.models import EveAppCredentials
# from esi_link.esi_auth.protocols import AppCredentialsProviderProtocol

# logger = logging.getLogger(__name__)


# class CredentialsProvider(AppCredentialsProviderProtocol):
#     def __init__(self, credentials_file: str | Path):
#         """Provides app credentials from a JSON file."""
#         self.credentials_file = Path(credentials_file)

#     def get_credentials(self) -> EveAppCredentials:
#         """Load the app credentials from the JSON file."""
#         try:
#             credentials = EveAppCredentials.model_validate_json(
#                 self.credentials_file.read_text()
#             )
#             self._credentials = credentials
#         except FileNotFoundError as e:
#             logger.error(f"App credentials file not found at {self.credentials_file}")
#             raise e
#         except Exception as e:
#             logger.error(f"Error reading app credentials: {e}")
#             raise e
#         return credentials

#     def has_credentials(self) -> bool:
#         """Check if the credentials file exists."""
#         return self.credentials_file.is_file()

#     def add_credentials(self, credentials: EveAppCredentials) -> None:
#         """Add new credentials to the provider and save them to the JSON file."""
#         try:
#             self.credentials_file.write_text(credentials.model_dump_json())
#             logger.info(f"App credentials saved to {self.credentials_file}")
#         except Exception as e:
#             logger.error(f"Error saving app credentials: {e}")
#             raise e

#     def remove_credentials(self) -> None:
#         """Remove the credentials file from the provider."""
#         if not self.credentials_file.is_file():
#             logger.warning(
#                 f"Remove Credentials: No credentials file found at {self.credentials_file} to remove."
#             )
#             return
#         try:
#             self.credentials_file.unlink()
#             logger.info(f"App credentials removed from {self.credentials_file}")
#         except FileNotFoundError as e:
#             logger.error(f"App credentials file not found at {self.credentials_file}")
#             raise e
#         except Exception as e:
#             logger.error(f"Error removing app credentials: {e}")
#             raise e
