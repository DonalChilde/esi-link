"""Module for executing groups of ESI requests."""

import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter

import aiohttp

from esi_link.models_and_protocols import (
    HttpRequestExecutorProtocol,
    RequestGroup,
    RequestGroupExecutorProtocol,
    RequestGroupValidatorProtocol,
    RequestValidatorProtocol,
    Response,
    ResponseGroup,
    RuntimeGroupInfoGeneratorProtocol,
    RuntimeRequest,
    RuntimeRequestInfoGeneratorProtocol,
)

RequestExecutionStrategy = Callable[
    [list[RuntimeRequest], HttpRequestExecutorProtocol], Awaitable[list[Response]]
]


class GroupExecutor(RequestGroupExecutorProtocol):
    def __init__(
        self,
        request_executor: HttpRequestExecutorProtocol,
        runtime_request_info: RuntimeRequestInfoGeneratorProtocol,
        runtime_group_info: RuntimeGroupInfoGeneratorProtocol,
        request_validator: RequestValidatorProtocol,
        request_group_validator: RequestGroupValidatorProtocol,
        execution_strategy: RequestExecutionStrategy | None = None,
    ) -> None:
        self._request_executor = request_executor
        self._runtime_request_info = runtime_request_info
        self._runtime_group_info = runtime_group_info
        self._request_validator = request_validator
        self._request_group_validator = request_group_validator
        self._execution_strategy: RequestExecutionStrategy = (
            execution_strategy or execute_requests_and_handle_responses_together
        )

    async def __call__(self, request_group: RequestGroup) -> ResponseGroup:
        """Execute a group of ESI requests and return their responses as a ResponseGroup."""
        runtime_group_info = self._runtime_group_info(request_group)
        group_metrics = runtime_group_info.metrics
        group_metrics.group_execution_started = perf_counter()
        self._request_group_validator(request_group)
        runtime_requests: list[RuntimeRequest] = []
        for request in request_group.requests.values():
            await self._request_validator(request)
            runtime_info = await self._runtime_request_info(request)
            runtime_requests.append(
                RuntimeRequest(request=request, runtime_info=runtime_info)
            )

        handled_responses = await self._execution_strategy(
            runtime_requests, self._request_executor
        )
        group_metrics.group_handlers_started = perf_counter()
        response_group = ResponseGroup(
            request_group=request_group,
            runtime_info=runtime_group_info,
            responses={r.request.request_id: r for r in handled_responses},
            group_handler_exception_messages=[],
            exceptions=[],
        )
        for handler in runtime_group_info.response_group_handlers:
            await handler(response_group)
        group_metrics.group_handlers_completed = perf_counter()
        group_metrics.group_execution_completed = perf_counter()
        return response_group


async def execute_all_requests_then_handle_responses(
    requests: list[RuntimeRequest], executor: HttpRequestExecutorProtocol
) -> list[Response]:
    """Execute all requests first, then handle their responses."""
    async with aiohttp.ClientSession() as session:
        tasks = [executor(runtime_request, session) for runtime_request in requests]
        responses = await asyncio.gather(*tasks)
    for response in responses:
        metrics = response.runtime_info.metrics
        metrics.handlers_started = perf_counter()
        for handler in response.runtime_info.response_handlers:
            await handler(response)
        metrics.handlers_completed = perf_counter()
        metrics.task_completed = perf_counter()
    return responses


async def execute_requests_and_handle_responses_together(
    requests: list[RuntimeRequest], executor: HttpRequestExecutorProtocol
) -> list[Response]:
    """Execute requests and handle their responses together."""
    async with aiohttp.ClientSession() as session:

        async def execute_and_handle(request: RuntimeRequest) -> Response:
            response = await executor(request, session)
            response.runtime_info.metrics.handlers_started = perf_counter()
            for handler in response.runtime_info.response_handlers:
                await handler(response)
            response.runtime_info.metrics.handlers_completed = perf_counter()
            response.runtime_info.metrics.task_completed = perf_counter()
            return response

        tasks = [execute_and_handle(runtime_request) for runtime_request in requests]
        responses = await asyncio.gather(*tasks)
    return responses
