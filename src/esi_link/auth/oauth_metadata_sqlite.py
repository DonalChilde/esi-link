"""Manage the metadata for the OAuth2 flow."""

import sqlite3

import httpx2
from jwt import PyJWKClient
from pydantic_core import from_json, to_json
from whenever import Instant

from esi_link import USER_AGENT
from esi_link.app_data.helpers import transaction
from esi_link.auth.models import OAuthMetadataTimestamped
from esi_link.settings import OAUTH_METADATA_URL

# @dataclass(slots=True, frozen=True)
# class OAuthMetadataTimestamped:
#     """A wrapper for OAuth metadata that includes a timestamp of when the metadata was fetched."""

#     metadata: dict[str, Any]
#     """The OAuth metadata as a dictionary."""
#     timestamp: int
#     """The timestamp of when the metadata was fetched, in nano_seconds since the epoch."""

#     @property
#     def timestamp_instant(self) -> Instant:
#         """Convert the timestamp to an Instant."""
#         return Instant.from_timestamp_nanos(self.timestamp)

#     @property
#     def issuers(self) -> list[str]:
#         """The issuers of the OAuth metadata."""
#         value = self.metadata["issuer"]
#         if isinstance(value, str):
#             return [value]
#         elif isinstance(value, list):
#             value = cast(list[str], value)
#             return value
#         else:
#             raise ValueError("Invalid issuer value in OAuth metadata.")

#     @property
#     def authorization_endpoint(self) -> str:
#         """The authorization endpoint of the OAuth metadata."""
#         return self.metadata["authorization_endpoint"]

#     @property
#     def token_endpoint(self) -> str:
#         """The token endpoint of the OAuth metadata."""
#         return self.metadata["token_endpoint"]

#     @property
#     def jwks_uri(self) -> str:
#         """The JWKS URI of the OAuth metadata."""
#         return self.metadata["jwks_uri"]

#     @property
#     def revocation_endpoint(self) -> str:
#         """The revocation endpoint of the OAuth metadata."""
#         return self.metadata["revocation_endpoint"]

#     @property
#     def code_challenge_methods_supported(self) -> list[str]:
#         """The code challenge methods supported by the OAuth metadata."""
#         return self.metadata["code_challenge_methods_supported"]

#     @property
#     def token_endpoint_auth_signing_alg_values_supported(self) -> list[str]:
#         """The token endpoint auth signing algorithms supported by the OAuth metadata."""
#         return self.metadata["token_endpoint_auth_signing_alg_values_supported"]


# OAuthMetadataTimestampedRoot = RootModel[OAuthMetadataTimestamped]


class OAuthMetadataSqliteCache:
    def __init__(
        self,
        connection: sqlite3.Connection,
        cache_ttl: int = 86400,
        metadata_url: str = OAUTH_METADATA_URL,
    ):
        """Manage the disk cache for OAuth metadata.

        Args:
            connection: The SQLite connection to use for caching metadata.
            cache_ttl: Time-to-live for the cached metadata, in seconds. Default is 86400 (1 day).
            metadata_url: The URL to fetch the metadata from if the cache is expired or does not exist. Default is OAUTH_METADATA_URL.
        """
        self._connection = connection
        self._cache_ttl = cache_ttl
        self._metadata_url = metadata_url
        self._cached_metadata: OAuthMetadataTimestamped | None = None
        self._jwks_client: PyJWKClient | None = None
        self._timestamped_metadata: OAuthMetadataTimestamped | None = None
        self._initialize_cache()

    def _load_metadata_from_db(self) -> OAuthMetadataTimestamped | None:
        """Load the cached metadata from db."""
        sql = "SELECT timestamped, metadata_json FROM OauthMetadataCache WHERE id = 0"
        with transaction(self._connection) as conn:
            row = conn.execute(sql).fetchone()
            if row is None:
                return None
            timestamped = row["timestamped"]
            metadata = from_json(row["metadata_json"])
            return OAuthMetadataTimestamped(
                metadata=metadata,
                timestamp=timestamped,
            )

    def _fetch_metadata_from_url(self) -> OAuthMetadataTimestamped:
        """Fetch the metadata from the URL."""
        response = httpx2.get(self._metadata_url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        metadata = response.json()
        return OAuthMetadataTimestamped(
            metadata=metadata, timestamp=Instant.now().timestamp_nanos()
        )

    def _save_metadata_to_cache(self, metadata: OAuthMetadataTimestamped) -> None:
        """Save the metadata to disk."""
        metadata_json = to_json(metadata.metadata)
        sql = """
        REPLACE INTO OauthMetadataCache (id, timestamped, metadata_json)
        VALUES (0, ?, ?)
        """
        with transaction(self._connection) as conn:
            conn.execute(sql, (metadata.timestamp, metadata_json))

    def _is_cache_valid(self) -> bool:
        """Check if the cached metadata is still valid based on the TTL."""
        if self._cached_metadata is None:
            return False
        now = Instant.now()
        cache_time = self._cached_metadata.timestamp_instant
        age = (now - cache_time).total("seconds")
        return age < self._cache_ttl

    def _fetch_and_cache_metadata(self) -> None:
        """Fetch the metadata from the URL and save it to the cache."""
        fetched_metadata = self._fetch_metadata_from_url()
        self._save_metadata_to_cache(fetched_metadata)
        self._cached_metadata = fetched_metadata

    def _initialize_cache(self) -> None:
        """Initialize the cache by loading metadata from the database or fetching from the URL if necessary."""
        cached_metadata = self._load_metadata_from_db()
        if cached_metadata is not None and self._is_cache_valid():
            self._cached_metadata = cached_metadata
        else:
            self._fetch_and_cache_metadata()

    # def __enter__(self) -> Self:
    #     """Load the metadata, either from cache or from the URL if the cache is invalid."""
    #     cached_metadata = self._load_metadata_from_db()
    #     if cached_metadata is not None and self._is_cache_valid():
    #         self._cached_metadata = cached_metadata
    #     else:
    #         fetched_metadata = self._fetch_metadata_from_url()
    #         self._save_metadata_to_cache(fetched_metadata)
    #         self._cached_metadata = fetched_metadata
    #     return self

    # def __exit__(
    #     self,
    #     exc_type: type[BaseException] | None,
    #     exc_val: BaseException | None,
    #     exc_tb: TracebackType | None,
    # ) -> None:
    #     """Clean up any resources if necessary. In this case, there are no resources to clean up."""
    #     pass

    def get(self) -> OAuthMetadataTimestamped:
        """Get the current OAuth metadata, either from cache or freshly fetched."""
        if self._cached_metadata is None:
            raise ValueError("OAuth metadata is not loaded.")
        if not self._is_cache_valid():
            self._fetch_and_cache_metadata()
        return self._cached_metadata

    # @property
    # def jwks_client(self) -> PyJWKClient:
    #     """Get a PyJWKClient for the JWKS URI provided in the metadata."""
    #     if self._jwks_client is None:
    #         self._jwks_client = PyJWKClient(
    #             self.metadata.jwks_uri, headers={"User-Agent": USER_AGENT}
    #         )
    #     return self._jwks_client
