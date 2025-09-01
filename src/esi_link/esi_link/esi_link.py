"""EsiLink module for managing concurrent requests to the Eve Online ESI API.

This module provides the EsiLink class, which handles batching, concurrency, error management,
and rate limiting for ESI API queries using asyncio and aiohttp.

Classes:
    EsiLink: Manages concurrent ESI API requests, error handling, and statistics.

Functions:
    None exported at module level.

Typical usage example:
    link = EsiLink(schema)
    result = link.do_query(query)
"""

import asyncio
import logging
from datetime import timedelta
from uuid import UUID

import aiohttp

from ..esi_schema.eve_openapi_protocol import EveOpenApiProtocol
from ..helpers.header_funcs import limit_remain, limit_reset
from ..helpers.now_utc import now_utc
from .models import EsiQuery, QueryResponse

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class EsiLink:
    """Handles concurrent requests and error management for Eve Online ESI API.

    Attributes:
        _schema (EveOpenApiProtocol): ESI schema for building requests.
        _max_concurrent_requests (int): Maximum concurrent requests allowed.
        _error_timeout_ends (datetime): When queries can resume after error.
        _default_timeout (int): Default timeout in seconds for error waits.
        _queue_remaining (int): Number of queries left in the queue.
        _stop_operations (bool): Flag to stop further queries after error.
        _skipped (int): Number of skipped queries due to errors.
        _errors (int): Number of errors encountered.
        _errors_remaining (int): Remaining error allowance before pausing.

    """

    def __init__(
        self, schema: EveOpenApiProtocol, max_concurrent_requests: int = 50
    ) -> None:
        self._error_timeout_ends = now_utc()
        """The time at which queries can resume."""
        self._default_timeout = 30
        self._schema = schema
        self._max_concurrent_requests = max_concurrent_requests
        self._queue_remaining: int = 0
        self._stop_operations = False
        self._skipped = 0
        self._errors = 0
        self._errors_remaining = 100

    def _reset_stats(self):
        self._queue_remaining = 0
        self._stop_operations = False
        self._skipped = 0
        self._errors = 0

    async def _wait_for_error_limit_reset(self):
        wait_for = 0
        if self._errors_remaining < 10:
            if self._error_timeout_ends is None:
                wait_for = self._default_timeout
            else:
                wait_for = self._error_timeout_ends - now_utc()
                wait_for = wait_for.total_seconds()
        if wait_for > 0:
            await asyncio.sleep(wait_for)

    async def _worker(
        self,
        name: str,
        queue: asyncio.Queue[EsiQuery],
        session: aiohttp.ClientSession,
        result: dict[UUID, QueryResponse],
    ):
        """Async worker for processing ESI queries from a queue.

        Args:
            name (str): Worker name for logging.
            queue (asyncio.Queue[EsiQuery]): Queue of queries to process.
            session (aiohttp.ClientSession): HTTP session for requests.
            result (dict[UUID, QueryResponse]): Dictionary to store results.

        """
        while True:
            query = await queue.get()
            await self._wait_for_error_limit_reset()
            self._queue_remaining = queue.qsize()
            if self._stop_operations:
                self._skipped += 1
                logger.info(
                    f"{name} skipping query {query['query_id']} due to previous errors."
                )
                queue.task_done()
                continue
            try:
                response = await self._do_get_query(
                    query=query,
                    session=session,
                )
                result[query["query_id"]] = response
                if response.status_code >= 400:
                    self._errors += 1
                    self._errors_remaining = limit_remain(response.headers)
                    time_out = limit_reset(response.headers) or self._default_timeout
                    if time_out != -1:
                        self._error_timeout_ends = now_utc() + timedelta(
                            seconds=time_out
                        )

            except Exception as e:
                logger.error(f"{name} error processing query {query['query_id']}: {e}")
                if not self._stop_operations:
                    self._stop_operations = True
                    # self._error_timeout_ends = now_utc() + timedelta(seconds=30)
            finally:
                queue.task_done()

    def do_query(self, query: EsiQuery) -> QueryResponse:
        """Executes a single ESI API query synchronously.

        Args:
            query (EsiQuery): The query to execute.

        Returns:
            QueryResponse: The response from the ESI API.

        Raises:
            Exception: If the query fails or the API returns an error.
        """
        return self.do_queries({query["query_id"]: query})[query["query_id"]]

    def do_queries(self, queries: dict[UUID, EsiQuery]) -> dict[UUID, QueryResponse]:
        """Executes multiple ESI API queries concurrently.

        Args:
            queries (dict[UUID, EsiQuery]): Dictionary of queries to execute.

        Returns:
            dict[UUID, QueryResponse]: Dictionary of responses keyed by query ID.

        Raises:
            Exception: If any query fails or the API returns an error.
        """
        self._reset_stats()
        if len(queries) > self._max_concurrent_requests:
            workers = self._max_concurrent_requests
        else:
            workers = len(queries)
        self._queue_remaining = len(queries)

        result = asyncio.run(self._run_tasks(workers, queries))
        return result

    async def _run_tasks(
        self,
        workers: int,
        queries: dict[UUID, EsiQuery],
    ):
        queue: asyncio.Queue[EsiQuery] = asyncio.Queue()
        result: dict[UUID, QueryResponse] = {}
        for query in queries.values():
            queue.put_nowait(query)
        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(self._worker(f"Worker-{i}", queue, session, result))
                for i in range(1, workers + 1)
            ]
            await asyncio.gather(*tasks)
        return result

    def _inject_compatability_date(self, headers):
        pass

    async def _do_get_query(
        self,
        query: EsiQuery,
        session: aiohttp.ClientSession,
    ) -> QueryResponse:
        url = self._schema.build_url(
            operation_id=query["operation"],
            path_params=query["path_parameters"],
            query_params={},
            include_query=False,
        )
        headers = query["headers"]
        headers["X-Esi-Compatibility-Date"] = self._schema.compatibility_date
        async with session.request(
            method=self._schema.operation_method(query["operation"]),
            url=url,
            headers=headers,
            params=query["query_parameters"],
        ) as response:
            async with response:
                match response.status:
                    case 200:
                        logger.debug(
                            f"{response.method} {response.real_url} returned "
                            f"{response.status} {response.reason}"
                        )
                    case 304:
                        logger.debug(
                            f"{response.method} {response.real_url} returned "
                            f"{response.status} {response.reason}"
                        )
                    case status_code if 400 <= status_code < 500:
                        logger.warning(
                            f"{response.method} {response.real_url} returned "
                            f"{response.status} {response.reason}"
                        )
                    case status_code if 500 <= status_code < 600:
                        logger.error(
                            f"{response.method} {response.real_url} returned "
                            f"{response.status} {response.reason}"
                        )
                    case _:
                        logger.error(
                            f"UNUSUAL STATUS: {response.method} {response.real_url} returned "
                            f"{response.status} {response.reason}"
                        )
                text = await response.text()
                return QueryResponse(
                    query_id=query["query_id"],
                    status_code=response.status,
                    status_reason=response.reason or "",
                    headers=tuple(response.headers.items()),
                    text=text,
                    real_url=str(response.real_url),
                    completed_on=now_utc().isoformat(),
                )
