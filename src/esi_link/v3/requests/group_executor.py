import asyncio
from collections.abc import Awaitable, Callable

import aiohttp

from esi_link.v3.models import RequestGroup, Response, ResponseGroup, RuntimeRequest
from esi_link.v3.protocols import (
    HttpRequestExecutorProtocol,
    RequestGroupExecutorProtocol,
    RequestGroupValidatorProtocol,
    RequestValidatorProtocol,
    RuntimeGroupInfoGeneratorProtocol,
    RuntimeRequestInfoGeneratorProtocol,
)

RequestExecutionStrategy = Callable[
    [list[RuntimeRequest], HttpRequestExecutorProtocol], Awaitable[list[Response]]
]


class GroupExecutor(RequestGroupExecutorProtocol):
    def __init__(
        self,
        request_executor: HttpRequestExecutorProtocol | None = None,
        runtime_request_info: RuntimeRequestInfoGeneratorProtocol | None = None,
        runtime_group_info: RuntimeGroupInfoGeneratorProtocol | None = None,
        request_validator: RequestValidatorProtocol | None = None,
        request_group_validator: RequestGroupValidatorProtocol | None = None,
        execution_strategy: RequestExecutionStrategy | None = None,
    ) -> None:
        # TODO after full implementation, ensure default values set, then can remove the none checks in __call__
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
        if self._runtime_request_info is None:
            raise ValueError("No runtime info generator provided.")
        if self._runtime_group_info is None:
            raise ValueError("No runtime group info generator provided.")
        if self._request_executor is None:
            raise ValueError("No request executor provided.")
        if self._request_group_validator is None:
            raise ValueError("No request group validator provided.")
        if self._request_validator is None:
            raise ValueError("No request validator provided.")

        runtime_requests: list[RuntimeRequest] = []
        for request in request_group.requests.values():
            runtime_info = await self._runtime_request_info(request)
            runtime_requests.append(
                RuntimeRequest(request=request, runtime_info=runtime_info)
            )
        runtime_group_info = self._runtime_group_info(request_group)
        handled_responses = await self._execution_strategy(
            runtime_requests, self._request_executor
        )
        for handler in runtime_group_info.response_group_handlers:
            await handler(request_group, handled_responses)

        return ResponseGroup(
            request_group=request_group,
            runtime_info=runtime_group_info,
            responses={r.request.request_id: r for r in handled_responses},
        )


async def execute_all_requests_then_handle_responses(
    requests: list[RuntimeRequest], executor: HttpRequestExecutorProtocol
) -> list[Response]:
    """Execute all requests first, then handle their responses."""
    async with aiohttp.ClientSession() as session:
        tasks = [executor(runtime_request, session) for runtime_request in requests]
        responses = await asyncio.gather(*tasks)
    for response in responses:
        for handler in response.runtime_info.response_handlers:
            await handler(response)
    return responses


async def execute_requests_and_handle_responses_together(
    requests: list[RuntimeRequest], executor: HttpRequestExecutorProtocol
) -> list[Response]:
    """Execute requests and handle their responses together."""
    async with aiohttp.ClientSession() as session:

        async def execute_and_handle(request: RuntimeRequest) -> Response:
            response = await executor(request, session)
            for handler in response.runtime_info.response_handlers:
                await handler(response)
            return response

        tasks = [execute_and_handle(runtime_request) for runtime_request in requests]
        responses = await asyncio.gather(*tasks)
    return responses
