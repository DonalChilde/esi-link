"""Manage the metadata for the OAuth2 flow."""

from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Self, cast

import httpx2
from jwt import PyJWKClient
from pydantic import RootModel
from whenever import Instant

from esi_link.rewrite import USER_AGENT
from esi_link.rewrite.settings import OAUTH_METADATA_URL

AUDIENCE = "EVE Online"


@dataclass(slots=True, frozen=True)
class OAuthMetadataTimestamped:
    """A wrapper for OAuth metadata that includes a timestamp of when the metadata was fetched."""

    metadata: dict[str, Any]
    """The OAuth metadata as a dictionary."""
    timestamp: int
    """The timestamp of when the metadata was fetched, in seconds since the epoch."""

    @property
    def issuers(self) -> list[str]:
        """The issuers of the OAuth metadata."""
        value = self.metadata["issuer"]
        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            value = cast(list[str], value)
            return value
        else:
            raise ValueError("Invalid issuer value in OAuth metadata.")

    @property
    def authorization_endpoint(self) -> str:
        """The authorization endpoint of the OAuth metadata."""
        return self.metadata["authorization_endpoint"]

    @property
    def token_endpoint(self) -> str:
        """The token endpoint of the OAuth metadata."""
        return self.metadata["token_endpoint"]

    @property
    def jwks_uri(self) -> str:
        """The JWKS URI of the OAuth metadata."""
        return self.metadata["jwks_uri"]

    @property
    def revocation_endpoint(self) -> str:
        """The revocation endpoint of the OAuth metadata."""
        return self.metadata["revocation_endpoint"]

    @property
    def code_challenge_methods_supported(self) -> list[str]:
        """The code challenge methods supported by the OAuth metadata."""
        return self.metadata["code_challenge_methods_supported"]

    @property
    def token_endpoint_auth_signing_alg_values_supported(self) -> list[str]:
        """The token endpoint auth signing algorithms supported by the OAuth metadata."""
        return self.metadata["token_endpoint_auth_signing_alg_values_supported"]


OAuthMetadataTimestampedRoot = RootModel[OAuthMetadataTimestamped]


class OAuthMetadataDiskCache:
    def __init__(
        self,
        cache_file: Path | None = None,
        cache_ttl: int = 3600,
        metadata_url: str = OAUTH_METADATA_URL,
    ):
        """Manage the disk cache for OAuth metadata.

        Args:
            cache_file: The file path to store the cached metadata. If None, caching is disabled.
            cache_ttl: Time-to-live for the cached metadata, in seconds. Default is 3600 (1 hour).
            metadata_url: The URL to fetch the metadata from if the cache is expired or does not exist. Default is OAUTH_METADATA_URL.
        """
        self._cache_file = cache_file
        self._cache_ttl = cache_ttl
        self._metadata_url = metadata_url
        self._cached_metadata: OAuthMetadataTimestamped | None = None
        self._jwks_client: PyJWKClient | None = None
        self._timestamped_metadata: OAuthMetadataTimestamped | None = None

    def _load_metadata_from_cache(self) -> OAuthMetadataTimestamped:
        """Load the cached metadata from disk."""
        if self._cache_file is None or not self._cache_file.exists():
            raise ValueError("Cached OAuth metadata does not exist.")
        with self._cache_file.open("r") as f:
            text = f.read()
            cached_metadata = OAuthMetadataTimestampedRoot.model_validate_json(
                text
            ).root
        return cached_metadata

    def _fetch_metadata_from_url(self) -> OAuthMetadataTimestamped:
        """Fetch the metadata from the URL."""
        response = httpx2.get(self._metadata_url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        metadata = response.json()
        return OAuthMetadataTimestamped(
            metadata=metadata, timestamp=Instant.now().timestamp()
        )

    def _save_metadata_to_cache(self, metadata: OAuthMetadataTimestamped) -> None:
        """Save the metadata to disk."""
        if self._cache_file is None:
            raise ValueError(
                "Cache file path is not set, cannot save metadata to cache."
            )
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        with self._cache_file.open("w") as f:
            f.write(
                OAuthMetadataTimestampedRoot(root=metadata).model_dump_json(indent=2)
            )

    def _is_cache_valid(self) -> bool:
        """Check if the cached metadata is still valid based on the TTL."""
        if self._cache_file is None or not self._cache_file.exists():
            return False
        try:
            cached_metadata = self._load_metadata_from_cache()
            return (
                Instant.now().timestamp() - cached_metadata.timestamp < self._cache_ttl
            )
        except Exception:
            return False

    def __enter__(self) -> Self:
        """Load the metadata, either from cache or from the URL if the cache is invalid."""
        if self._cache_file is not None and self._cache_file.exists():
            self._cached_metadata = self._load_metadata_from_cache()
            if not self._is_cache_valid():
                self._cached_metadata = self._fetch_metadata_from_url()
                self._save_metadata_to_cache(self._cached_metadata)
        else:
            self._cached_metadata = self._fetch_metadata_from_url()
            if self._cache_file is not None:
                self._save_metadata_to_cache(self._cached_metadata)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Clean up any resources if necessary. In this case, there are no resources to clean up."""
        pass

    @property
    def metadata(self) -> OAuthMetadataTimestamped:
        """Get the current OAuth metadata, either from cache or freshly fetched."""
        if self._cached_metadata is None:
            raise ValueError("OAuth metadata is not loaded.")
        return self._cached_metadata

    # @property
    # def jwks_client(self) -> PyJWKClient:
    #     """Get a PyJWKClient for the JWKS URI provided in the metadata."""
    #     if self._jwks_client is None:
    #         self._jwks_client = PyJWKClient(
    #             self.metadata.jwks_uri, headers={"User-Agent": USER_AGENT}
    #         )
    #     return self._jwks_client
