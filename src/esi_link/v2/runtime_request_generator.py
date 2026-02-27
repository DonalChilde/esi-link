"""Functions for working with EsiRequests."""

import logging
from copy import deepcopy

from esi_link.v2 import USER_AGENT
from esi_link.v2.models import (
    AuthProviderProtocol,
    EsiRequest,
    EsiRequestError,
    EsiRuntimeRequest,
    IndexedOperation,
    RuntimeRequestGeneratorProtocol,
    RuntimeRequestInfo,
    UrlGeneratorProtocol,
)

logger = logging.getLogger(__name__)


class RuntimeRequestGenerator(RuntimeRequestGeneratorProtocol):
    def __init__(
        self,
        operation: IndexedOperation,
        compatibility_date: str,
        auth_provider: AuthProviderProtocol,
        url_generator: UrlGeneratorProtocol,
        language: str,
    ) -> None:
        """Initialize the RuntimeRequestGenerator with the necessary components."""
        self.operation = operation
        self.compatibility_date = compatibility_date
        self.auth_provider = auth_provider
        self.url_generator = url_generator
        self.language = language

    def generate_runtime_info(self, request: EsiRequest) -> RuntimeRequestInfo:
        """Generate the runtime information for an ESI request based on its parameters."""
        url_info = self.url_generator.generate_url_info(request)

        runtime_info = RuntimeRequestInfo(
            path_url=url_info.path_url,
            additional_query_params={},
            method=self.operation.method,
            is_paged=self.operation.is_paged,
            is_auth=self.operation.auth_required,
            headers=self._generate_headers(request),
            timeout=10,
            cache_key=url_info.cache_key if self.operation.is_cached else None,
        )
        return runtime_info

    def get_runtime_request(self, request: EsiRequest) -> EsiRuntimeRequest:
        """Generate the full EsiRuntimeRequest for a given EsiRequest, including runtime info.

        A deepcopy of the request is used to avoid mutation issues with handlers and retries.
        """
        info = self.generate_runtime_info(request)
        runtime_request = EsiRuntimeRequest(
            request=deepcopy(request),
            runtime_info=info,
        )
        return runtime_request

    def _get_auth_headers(self, request: EsiRequest) -> dict[str, str]:
        if self.operation.auth_required and not request.auth_parameters:
            raise EsiRequestError(
                f"Operation ID {request.operation_id} requires authentication.",
                request,
            )
        if not request.auth_parameters:
            return {}
        character_id = request.auth_parameters.character_id
        client_alias = request.auth_parameters.client_alias
        try:
            auth_headers = self.auth_provider.get_auth_headers(
                character_id=character_id, client_alias=client_alias
            )
        except Exception as e:
            logger.error(
                f"Error getting auth headers for character_id {character_id} and client_alias {client_alias}: {e}"
            )
            raise EsiRequestError(
                f"Error getting auth headers for character_id {character_id} and client_alias {client_alias}: {e}",
                request,
            ) from e
        return auth_headers

    def _generate_headers(self, request: EsiRequest) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.operation.auth_required and request.auth_parameters:
            auth_headers = self.auth_provider.get_auth_headers(
                character_id=request.auth_parameters.character_id,
                client_alias=request.auth_parameters.client_alias,
            )
            headers.update(auth_headers)
        headers["User-Agent"] = USER_AGENT
        headers["Accept-Language"] = self.language
        headers["X-Compatibility-Date"] = self.compatibility_date
        headers.update(self._get_auth_headers(request))
        return headers
