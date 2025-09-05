from uuid import UUID

from esi_link.esi_client.models import EsiQuery, LinkCacheMetadata, QueryResponse
from esi_link.esi_schema.eve_openapi_protocol import EveOpenApiProtocol
from esi_link.helpers import header_funcs as HF
from esi_link.helpers.cache_id_from_url import cache_id_from_url


def make_cache_key(query: EsiQuery, schema_api: EveOpenApiProtocol) -> UUID:
    """Generate a unique cache key for the given query and schema.

    Args:
        query (EsiQuery): The ESI query.
        schema (EveOpenApiProtocol): The ESI schema.

    Returns:
        UUID: The cache key for the query.
    """
    url = schema_api.build_url(
        operation_id=query.operation_id,
        path_params=query.path_parameters,
        query_params=query.query_parameters,
        include_query=True,
    )
    cache_key = cache_id_from_url(url)
    return cache_key


def build_metadata(
    query: EsiQuery,
    response: QueryResponse,
    schema_api: EveOpenApiProtocol,
) -> LinkCacheMetadata:
    """Build cache metadata from the query and response.

    Args:
        query (EsiQuery): The ESI query.
        response (QueryResponse): The ESI response.

    Returns:
        LinkCacheMetadata: The cache metadata.
    """
    cache_key = make_cache_key(query, schema_api=schema_api)
    expires = HF.expires(response.headers)
    etag = HF.etag(response.headers)
    last_modified_value = HF.last_modified(response.headers)
    last_checked = response.completed_on

    metadata = LinkCacheMetadata(
        cache_key=cache_key,
        expires=expires,
        etag=etag,
        last_modified=last_modified_value,
        last_checked=last_checked,
    )
    return metadata
