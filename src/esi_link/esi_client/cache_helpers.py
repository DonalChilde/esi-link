from uuid import UUID

from esi_link.esi_client.models import EsiQuery, LinkCacheMetadata
from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol
from esi_link.helpers import header_funcs as HF
from esi_link.helpers.cache_id_from_url import cache_id_from_url


def is_cachable(query: EsiQuery, esi_api: EsiApiProtocol) -> bool:
    """Determine if the given query is cachable.

    Args:
        query (EsiQuery): The ESI query.
        esi_api (EsiApiProtocol): The ESI API schema.
    """
    operation = esi_api.indexed_operation(query.operation_id)
    cachable = all((operation.method.lower() == "get",))
    return cachable


def make_cache_key(query: EsiQuery, esi_api: EsiApiProtocol) -> UUID:
    """Generate a unique cache key for the given query and schema.

    Args:
        query (EsiQuery): The ESI query.
        esi_api (EsiApiProtocol): The ESI API schema.

    Returns:
        UUID: The cache key for the query.
    """
    url = esi_api.build_url(
        operation_id=query.operation_id,
        path_params=query.path_parameters,
        query_params=query.query_parameters,
        include_query=True,
    )
    cache_key = cache_id_from_url(url)
    return cache_key


def build_metadata(
    query: EsiQuery,
    esi_api: EsiApiProtocol,
) -> LinkCacheMetadata:
    """Build cache metadata from the query and response.

    Args:
        query (EsiQuery): The ESI query.
        response (QueryResponse): The ESI response.
        esi_api (EsiApiProtocol): The ESI API schema.

    Returns:
        LinkCacheMetadata: The cache metadata.
    """
    if query.response is None:
        raise ValueError("Query response is None, cannot build metadata.")
    cache_key = make_cache_key(query, esi_api=esi_api)
    expires = HF.expires(query.response.headers)
    etag = HF.etag(query.response.headers)
    last_modified_value = HF.last_modified(query.response.headers)
    last_checked = query.response.completed_on

    metadata = LinkCacheMetadata(
        cache_key=cache_key,
        url=query.response.real_url,
        expires=expires,
        etag=etag,
        last_modified=last_modified_value,
        last_checked=last_checked,
    )
    return metadata
