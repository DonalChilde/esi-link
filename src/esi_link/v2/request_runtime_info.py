"""Functions for working with EsiRequests."""

import logging

from esi_link.v2 import USER_AGENT
from esi_link.v2.models import (
    AuthProviderProtocol,
    EsiRequest,
    EsiRequestError,
    IndexedOperation,
    RuntimeInfoGeneratorProtocol,
    RuntimeRequestInfo,
    UrlGeneratorProtocol,
)

logger = logging.getLogger(__name__)


# def populate_runtime_info(
#     request: EsiRequest,
#     schema: IndexedEsiSchema,
#     auth_provider: AuthProviderProtocol,
#     lang: str = "en",
# ) -> None:
#     """Populate the runtime info for an ESI request based on the indexed schema."""
#     if request.operation_id not in schema.operations:
#         raise ValueError(f"Operation ID {request.operation_id} not found in schema")
#     operation = schema.operations[request.operation_id]
#     base_url = schema.servers[0]["url"]
#     path_template = operation.path
#     headers: dict[str, str] = {}
#     if operation.auth_required and request.auth_parameters:
#         auth_headers = auth_provider.get_auth_headers(
#             character_id=request.auth_parameters.character_id,
#             client_alias=request.auth_parameters.client_alias,
#         )
#         headers.update(auth_headers)
#     headers["User-Agent"] = USER_AGENT
#     headers["Accept-Language"] = lang
#     headers["X-Compatibility-Date"] = schema.version
#     url = build_url(
#         path_parameters=request.path_parameters or {},
#         query_parameters=request.query_parameters or {},
#         base_url=base_url,
#         path_template=path_template,
#     )
#     if operation.is_cached:
#         cache_key = cache_key_from_url(url)
#     else:
#         cache_key = None
#     runtime = RuntimeRequestInfo(
#         url=url,
#         base_url=base_url,
#         path_template=path_template,
#         additional_query_params={},
#         method=operation.method,
#         is_paged=operation.is_paged,
#         is_auth=operation.auth_required,
#         headers=headers,
#         timeout=10,
#         cache_key=cache_key,
#     )
#     request.runtime_info = runtime


class RuntimeInfoGenerator(RuntimeInfoGeneratorProtocol):
    def __init__(
        self,
        operation: IndexedOperation,
        compatibility_date: str,
        auth_provider: AuthProviderProtocol,
        url_generator: UrlGeneratorProtocol,
        language: str,
    ) -> None:
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
