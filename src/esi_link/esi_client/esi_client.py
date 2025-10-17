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

from esi_link.cache.cache_helpers import is_cachable, make_cache_key
from esi_link.esi_client.models import ResponseSource
from esi_link.esi_client.query_validator import (
    EsiQueryValidatorProtocol,
    ValidationError,
)

from ..cache.link_cache_protocol import CacheStatus, LinkCacheProtocol
from ..esi_schema.esi_api_protocol import EsiApiProtocol, SplitParameters
from ..helpers.header_funcs import last_modified, pages_available
from .esi_http import EsiHttp, EsiQuery

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class EsiClient:
    def __init__(
        self,
        esi_api: EsiApiProtocol,
        cache: LinkCacheProtocol,
        validator: EsiQueryValidatorProtocol | None = None,
        max_concurrent_requests: int = 50,
    ) -> None:
        self.esi_api = esi_api
        self.cache = cache
        self.link = EsiHttp(esi_api, max_concurrent_requests)
        self.validator = validator

    def query(self, esi_query: EsiQuery) -> None:
        esi_batch_query(
            queries=(esi_query,),
            cache=self.cache,
            esi_api=self.esi_api,
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
            esi_api=self.esi_api,
            esi_http=self.link,
        )
        return None

    def split_request_parameters(
        self, operation_id: str, parameters: Sequence[dict[str, str]]
    ) -> SplitParameters:
        """Split a list of request parameter {key:value} into their respective path, query, and header categories."""

        # NOTE this flattens the list of dicts into a single dict, which means that
        # repeated keys will be lost. This is a limitation of the current implementation.
        # To fully support repeated keys, the schema API and split_request_parameters
        # method would need to be updated to accept a list of values for each key.
        param_dict = {k: v for d in parameters for k, v in d.items()}
        return self.esi_api.split_request_parameters(operation_id, param_dict)

    def validate_query(self, esi_query: EsiQuery) -> None:
        """Validate the query against the ESI schema."""
        if self.validator:
            self.validator.validate(esi_query)

    def is_paged(self, esi_query: EsiQuery) -> bool:
        """Check if the operation is paged."""
        return self.esi_api.is_paged(esi_query.operation_id)


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
    pages = pages_available(query.response.headers)
    if pages < 1:
        raise ValueError(f"Invalid page count: {pages}. Expected >= 1.")
    if pages > 1000:  # Reasonable upper limit to prevent excessive requests
        logger.warning(f"Large page count detected: {pages}. This may take a while.")
    for page in range(2, pages + 1):
        paged_query = deepcopy(query)
        paged_query.query_parameters = {**query.query_parameters, "page": page}
        paged_queries.append(paged_query)
    return paged_queries


def paged_query(
    query: EsiQuery,
    cache: LinkCacheProtocol,
    esi_api: EsiApiProtocol,
    esi_http: EsiHttp,
) -> None:
    """Execute a paged ESI query, handling cache, paging, and errors.

    This function executes a single ESI query that may involve multiple pages of results.
    It is ment to be called from within a batch query operation, and expects the cache resource
    to be already open.

    Modifies the input query in-place by setting its response attribute with
    the combined response data from all pages.

    Args:
        query (EsiQuery): The ESI query to execute. Modified in-place.
        cache (LinkCacheProtocol): The cache protocol. Expects the cache to be open.
        esi_api (EsiApiProtocol): The ESI API.
        esi_http (EsiHttp): The ESI HTTP client for executing queries.

    Returns:
        None: The query object is modified in-place.

    Raises:
        ValueError: If an error occurs during query execution or validation.
    """
    logger.info(
        f"Processing paged query {query.query_id} for operation {query.operation_id}"
    )
    # See if we can satisfy the query from cache
    if is_cachable(query, esi_api):
        cache_key = make_cache_key(query, esi_api)
        cache_status = cache.status(cache_key)
        if cache_status is CacheStatus.HIT:
            query.response = cache.get_response(cache_key)
            query.response.source = ResponseSource.CACHE
            return
        elif cache_status is CacheStatus.STALE:
            # If the cache is stale, we need to revalidate it
            _inject_etag(query, cache, esi_api)
    esi_http.do_query(query)
    if query.response is None:
        raise ValueError(
            f"Response data is None for query {query.query_id}. Check logs for more information."
        )
    if is_cachable(query, esi_api):
        if query.response.status_code == 304:
            # If we get a 304 response, we can update and return the cached response
            cache_key = make_cache_key(query, esi_api)
            query.response.source = ResponseSource.LIVE_304
            cache.update_304(cache_key, query)
            response = cache.get_response(cache_key)
            query.response = response
            return

    if query.response.status_code != 200:
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
                f"Last-Modified header mismatch for paged query {p_query.query_id}. Data changed on server during request. Try Again. Check logs for more information."
            )
        query.response.paged_text.append(p_query.response.text)
    if not confirm_all_pages_received(query):
        raise ValueError(
            f"Not all pages received for query {query.query_id}. Check logs for more information."
        )
    query.response.source = ResponseSource.LIVE
    if is_cachable(query, esi_api):
        # add the completed response to the cache.
        cache_key = make_cache_key(query, esi_api)
        metadata = cache.build_metadata(query=query, schema_api=esi_api)
        cache.set(cache_key, metadata, query.response)
    return None


def confirm_all_pages_received(query: EsiQuery) -> bool:
    """Confirm that all pages for a paged query have been received.

    Args:
        query (EsiQuery): The ESI query to check.

    Returns:
        bool: True if all pages have been received, False otherwise.
    """
    if query.response is None:
        return False
    pages = pages_available(query.response.headers) if query.response else 0
    if pages != len(query.response.paged_text) + 1:
        logger.error(
            f"Not all pages received for query {query.query_id}. Expected {pages}, got {len(query.response.paged_text) + 1}."
        )
        return False
    return True


def esi_batch_query(
    queries: Sequence[EsiQuery],
    cache: LinkCacheProtocol,
    esi_api: EsiApiProtocol,
    esi_http: EsiHttp,
) -> None:
    """Execute a batch of ESI queries, handling cache, paging, and errors.

    Args:
        queries (dict[UUID, EsiQuery]): Dictionary of queries to execute.
        cache (LinkCacheProtocol): The cache protocol.
        esi_api (EsiApiProtocol): The ESI API.
        link (EsiLink): The ESI link for executing queries.
        fail_on_error (bool, optional): Whether to raise on error. Defaults to False.

    Returns:
        dict[UUID, QueryResponse]: Dictionary of responses keyed by query ID.

    Raises:
        ValueError: If an error occurs and fail_on_error is True.
    """

    not_paged: list[EsiQuery] = []
    paged: list[EsiQuery] = []
    # split queries into paged and not paged
    for query in queries:
        if esi_api.is_paged(query.operation_id):
            paged.append(query)
        else:
            not_paged.append(query)
    logger.info(
        f"Processing {len(queries)} queries: {len(paged)} paged, {len(not_paged)} non-paged."
    )
    with cache as opened_cache:
        for query in not_paged:
            # see if we can satisfy the query from cache
            if is_cachable(query, esi_api):
                cache_key = make_cache_key(query, esi_api)
                cache_status = opened_cache.status(cache_key)
                if cache_status is CacheStatus.HIT:
                    response = opened_cache.get_response(cache_key)
                    query.response = response
                    response.source = ResponseSource.CACHE
                elif cache_status is CacheStatus.STALE:
                    # If the cache is stale, we need to revalidate it
                    _inject_etag(query, opened_cache, esi_api)
        # execute all non-paged queries that still need a response
        incomplete_queries = [x for x in not_paged if x.response is None]
        logger.info(
            f"Executing {len(incomplete_queries)} incomplete queries out of {len(not_paged)} non-paged queries."
        )
        esi_http.do_queries(incomplete_queries)

        for query in not_paged:
            if query.response is None:
                logger.error(f"Response data is None for query {query!r}.")
                raise ValueError(
                    f"Response data is None for query {query.query_id}. Check logs for more information."
                )

            if is_cachable(query, esi_api):
                if query.response.status_code == 304:
                    # If we get a 304 response, we can return the cached response
                    cache_key = make_cache_key(query, esi_api)
                    opened_cache.update_304(cache_key, query)
                    query.response = opened_cache.get_response(cache_key)
                    query.response.source = ResponseSource.LIVE_304
                    continue
                elif (
                    query.response.status_code == 200
                    and query.response.source is not ResponseSource.CACHE
                ):
                    # If we get a 200 response, we need to update the cache
                    cache_key = make_cache_key(query, esi_api)
                    metadata = opened_cache.build_metadata(
                        query=query, schema_api=esi_api
                    )
                    query.response.source = ResponseSource.LIVE
                    opened_cache.set(cache_key, metadata, query.response)
                    continue
            query.response.source = ResponseSource.LIVE
            if query.response.status_code not in (200, 201, 204, 304):
                logger.error(f"Bad response for {query!r}.")
                raise ValueError(
                    f"Unexpected status code: {query.response.status_code} for {query.query_id}. Check logs for more information."
                )
        for query in paged:
            paged_query(
                query=query, cache=opened_cache, esi_api=esi_api, esi_http=esi_http
            )
