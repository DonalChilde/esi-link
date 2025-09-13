"""ESI client utilities for retrieving and caching data from the Eve Online ESI API.

This module provides functions for building, validating, and executing ESI queries,
including support for caching, paging, and batch operations. It is designed to handle
large numbers of concurrent requests efficiently and robustly.

Functions:
    _make_cache_key: Generate a cache key for a query.
    _validate_query: Validate a query against the ESI schema.
    _inject_etag: Inject ETag header from cache into a query.
    _build_pages_queries: Build queries for all pages of a paged response.
    paged_query: Execute a paged ESI query, handling cache and errors.
    esi_batch_query: Execute a batch of ESI queries, handling cache, paging, and errors.

Typical usage example:
    response = paged_query(query, cache, schema, link)
    results = esi_batch_query(queries, cache, schema, link)
"""

import logging
from collections.abc import Sequence
from copy import deepcopy

from esi_link.esi_client.cache_helpers import is_cachable, make_cache_key
from esi_link.esi_client.query_validator import (
    EsiQueryValidatorProtocol,
    ValidationError,
)

from ..esi_schema.esi_api_protocol import EsiApiProtocol, SplitParameters
from ..helpers.header_funcs import last_modified, page_count
from .esi_http import EsiHttp, EsiQuery
from .link_cache_protocol import CacheStatus, LinkCacheProtocol

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class EsiClient:
    def __init__(
        self,
        schema_api: EsiApiProtocol,
        cache: LinkCacheProtocol,
        validator: EsiQueryValidatorProtocol | None = None,
        max_concurrent_requests: int = 50,
    ) -> None:
        self.schema_api = schema_api
        self.cache = cache
        self.link = EsiHttp(schema_api, max_concurrent_requests)
        self.validator = validator

    def query(self, esi_query: EsiQuery) -> None:
        esi_batch_query(
            queries=(esi_query,),
            cache=self.cache,
            schema_api=self.schema_api,
            esi_http=self.link,
        )
        return None

    def batch_query(self, queries: Sequence[EsiQuery]) -> None:
        if self.validator:
            for query in queries:
                try:
                    self.validator.validate(query)
                except ValidationError as e:
                    logger.warning(f"Query validation failed: {e} for query {query!r}")
        esi_batch_query(
            queries=queries,
            cache=self.cache,
            schema_api=self.schema_api,
            esi_http=self.link,
        )
        return None

    def split_request_parameters(
        self, operation_id: str, parameters: dict[str, str] | Sequence[dict[str, str]]
    ) -> SplitParameters:
        """Split a list of request parameter {key:value} into their respective path, query, and header categories."""
        if isinstance(parameters, Sequence):
            param_dict = {k: v for d in parameters for k, v in d.items()}
        else:
            param_dict = parameters
        return self.schema_api.split_request_parameters(operation_id, param_dict)

    def validate_query(self, esi_query: EsiQuery) -> None:
        """Validate the query against the ESI schema."""
        if self.validator:
            self.validator.validate(esi_query)


# def make_cache_key(query: EsiQuery, schema_api: EveOpenApiProtocol) -> UUID:
#     """Generate a unique cache key for the given query and schema.

#     Args:
#         query (EsiQuery): The ESI query.
#         schema (EveOpenApiProtocol): The ESI schema.

#     Returns:
#         UUID: The cache key for the query.
#     """
#     url = schema_api.build_url(
#         operation_id=query.operation_id,
#         path_params=query.path_parameters,
#         query_params=query.query_parameters,
#         include_query=True,
#     )
#     cache_key = cache_id_from_url(url)
#     return cache_key


# def _validate_query(query: EsiQuery, schema_api: EveOpenApiProtocol) -> bool:
#     """Validate the query against the ESI schema.

#     Args:
#         query (EsiQuery): The ESI query.
#         schema (EveOpenApiProtocol): The ESI schema.

#     Returns:
#         bool: True if the query is valid, False otherwise.
#     """
#     valid = schema_api.validate_operation(
#         operation_id=query.operation_id,
#         path_params=query.path_parameters,
#         query_params=query.query_parameters,
#     )
#     return valid


def _inject_etag(
    query: EsiQuery, cache: LinkCacheProtocol, schema_api: EsiApiProtocol
) -> None:
    # get the etag from the cache
    cache_key = make_cache_key(query, schema_api)
    metadata = cache.get_cache_metadata(cache_key)
    etag = metadata.etag if metadata else ""
    if etag:
        query.headers["If-None-Match"] = etag


def _build_pages_queries(query: EsiQuery) -> Sequence[EsiQuery]:
    paged_queries: list[EsiQuery] = []
    if query.response is None:
        raise ValueError("Query response is None, cannot build paged queries.")
    pages = page_count(query.response.headers)
    for page in range(2, pages + 1):
        paged_query = deepcopy(query)
        paged_query.query_parameters = {**query.query_parameters, "page": page}
        paged_queries.append(paged_query)
    return paged_queries


def paged_query(
    query: EsiQuery,
    cache: LinkCacheProtocol,
    schema_api: EsiApiProtocol,
    esi_http: EsiHttp,
) -> None:
    """Execute a paged ESI query, handling cache, paging, and errors.

    Args:
        query (EsiQuery): The ESI query.
        cache (LinkCacheProtocol): The cache protocol.
        schema_api (EveOpenApiProtocol): The ESI schema.
        esi_http (EsiHttp): The ESI HTTP client for executing queries.
        fail_on_error (bool, optional): Whether to raise on error. Defaults to False.

    Returns:
        QueryResponse: The combined response for all pages.

    Raises:
        ValueError: If an error occurs and fail_on_error is True.
    """
    # _validate_query(query, schema_api)
    # response: QueryResponse | None = None
    if is_cachable(query, schema_api):
        cache_key = make_cache_key(query, schema_api)
        cache_status = cache.status(cache_key)
        if cache_status is CacheStatus.HIT:
            query.response = cache.get_response(cache_key)
            return
        elif cache_status is CacheStatus.STALE:
            # If the cache is stale, we need to revalidate it
            _inject_etag(query, cache, schema_api)
            esi_http.do_query(query)
            if query.response is None:
                raise ValueError(
                    f"Response data is None for query {query.query_id}. Check logs for more information."
                )
            if query.response.status_code == 304:
                # If we get a 304 response, we can update and return the cached response
                cache.update_304(cache_key, query)
                response = cache.get_response(cache_key)
                query.response = response
                return
    if query.response is None:
        esi_http.do_query(query)
    if query.response is None:
        raise ValueError(
            f"Response data is None for query {query.query_id}. Check logs for more information."
        )
    if query.response.status_code not in [200, 201, 204]:
        logger.error(f"Bad response for {query!r}")
        raise ValueError(
            f"Unexpected status code: {query.response.status_code} for {query.query_id}. Check logs for more information."
        )
    paged_queries = _build_pages_queries(query)
    esi_http.do_queries(paged_queries)
    parent_last_modified = last_modified(query.response.headers)
    for p_query in paged_queries:
        if p_query.response is None:
            logger.error(f"Response data is None for paged query {p_query!r}.")
            raise ValueError(
                f"Response data is None for paged query {p_query.query_id}. Check logs for more information."
            )
        if p_query.response.status_code != 200:
            logger.error(f"Bad response for {p_query!r}")
            raise ValueError(
                f"Unexpected status code: {p_query.response.status_code} for {p_query.query_id}. Check logs for more information."
            )
        if parent_last_modified != last_modified(p_query.response.headers):
            logger.error(
                f"Last-Modified header mismatch. parent={parent_last_modified}. {p_query!r}"
            )
            raise ValueError(
                f"Last-Modified header mismatch for paged query {p_query.query_id}. Check logs for more information."
            )
        query.response.paged_text.append(p_query.response.text)

    if is_cachable(query, schema_api):
        # add the completed response to the cache.
        cache_key = make_cache_key(query, schema_api)
        metadata = cache.build_metadata(query=query, schema_api=schema_api)
        cache.set(cache_key, metadata, query.response)
    return None


def esi_batch_query(
    queries: Sequence[EsiQuery],
    cache: LinkCacheProtocol,
    schema_api: EsiApiProtocol,
    esi_http: EsiHttp,
) -> None:
    """Execute a batch of ESI queries, handling cache, paging, and errors.

    Args:
        queries (dict[UUID, EsiQuery]): Dictionary of queries to execute.
        cache (LinkCacheProtocol): The cache protocol.
        schema (EveOpenApiProtocol): The ESI schema.
        link (EsiLink): The ESI link for executing queries.
        fail_on_error (bool, optional): Whether to raise on error. Defaults to False.

    Returns:
        dict[UUID, QueryResponse]: Dictionary of responses keyed by query ID.

    Raises:
        ValueError: If an error occurs and fail_on_error is True.
    """

    one_pass: list[EsiQuery] = list(queries)
    paged: list[EsiQuery] = []
    for query in queries:
        if schema_api.is_paged(query.operation_id):
            paged.append(query)
            one_pass.remove(query)
            if is_cachable(query, schema_api):
                cache_key = make_cache_key(query, schema_api)
                cache_status = cache.status(cache_key)
                if cache_status is CacheStatus.HIT:
                    response = cache.get_response(cache_key)
                    query.response = response
                    one_pass.remove(query)
                elif cache_status is CacheStatus.STALE:
                    # If the cache is stale, we need to revalidate it
                    _inject_etag(query, cache, schema_api)
    esi_http.do_queries(one_pass)
    for query in one_pass:
        if query.response is None:
            logger.error(f"Response data is None for query {query!r}.")
            raise ValueError(
                f"Response data is None for query {query.query_id}. Check logs for more information."
            )

        if is_cachable(query, schema_api):
            if query.response.status_code == 304:
                # If we get a 304 response, we can return the cached response
                cache_key = make_cache_key(query, schema_api)
                cache.update_304(cache_key, query)
                query.response = cache.get_response(cache_key)
            elif query.response.status_code == 200:
                # If we get a 200 response, we need to update the cache
                cache_key = make_cache_key(query, schema_api)
                metadata = cache.build_metadata(query=query, schema_api=schema_api)
                cache.set(cache_key, metadata, query.response)
        if query.response.status_code not in (200, 201, 204, 304):
            logger.error(f"Bad response for {query!r}.")
            raise ValueError(
                f"Unexpected status code: {query.response.status_code} for {query.query_id}. Check logs for more information."
            )
    for query in paged:
        paged_query(query=query, cache=cache, schema_api=schema_api, esi_http=esi_http)
