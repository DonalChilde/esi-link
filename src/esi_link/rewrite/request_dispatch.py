"""Function for dispatching requests."""

import asyncio
from uuid import UUID

import aiohttp
from aiolimiter import AsyncLimiter

from esi_link import USER_AGENT
from esi_link.rewrite.actions.response_action import do_response_action
from esi_link.rewrite.execution.request_executor import execute_request_with_cache
from esi_link.rewrite.protocols.cache_manager import (
    CacheManagerProtocol,
)
from esi_link.rewrite.protocols.schema_manager import SchemaManagerProtocol
from esi_link.rewrite.request.models import (
    Request,
    RequestGroup,
    Response,
    ResponseGroup,
)
from esi_link.rewrite.runtime.models import (
    FailedRuntimeResponse,
    RuntimeRequest,
    RuntimeResponse,
)
from esi_link.rewrite.runtime.runtime_request_factory import (
    generate_runtime_request,
)
from esi_link.rewrite.validation.models import FailedRequestValidation
from esi_link.rewrite.validation.request_validation_factory import validate_requests


async def dispatch_requests(
    requests: dict[UUID, Request],
    schema_manager: SchemaManagerProtocol,
    cache_manager: CacheManagerProtocol,
    authentication_headers: dict[int, dict[str, str]],
    requests_per: float = 100.0,
    time_period: float = 60.0,
) -> tuple[
    dict[UUID, Response],
    dict[UUID, FailedRequestValidation],
    dict[UUID, FailedRuntimeResponse],
]:
    """Dispatch requests and return the responses."""
    if not requests:
        raise ValueError("Requests must contain at least one request.")

    valid_requests, failed_request_validations = validate_requests(
        requests=requests,
        schema_manager=schema_manager,
        authorized_characters=set(authentication_headers.keys()),
    )

    runtime_requests: dict[UUID, RuntimeRequest] = {}
    for request_id, validated_request in valid_requests.items():
        runtime_request = generate_runtime_request(
            validated_request=validated_request,
            authorization_headers=authentication_headers,
            user_agent=USER_AGENT,
        )
        runtime_requests[request_id] = runtime_request

    async with aiohttp.ClientSession() as session:
        rate_limiter = AsyncLimiter(requests_per, time_period)

        async def execute_with_actions(
            request: RuntimeRequest,
        ) -> RuntimeResponse | FailedRuntimeResponse:
            response = await execute_request_with_cache(
                request=request,
                session=session,
                cache_manager=cache_manager,
                rate_limiter=rate_limiter,
            )
            for action in request.actions_after_response:
                # NOTE action might modify the response, so we need to update the response variable with the result of the action.
                response = await do_response_action(action=action, response=response)
            return response

        tasks = [
            execute_with_actions(request=request)
            for request in runtime_requests.values()
        ]
        runtime_responses = await asyncio.gather(*tasks)
    responses: dict[UUID, Response] = {}
    failed_runtime_responses: dict[UUID, FailedRuntimeResponse] = {}
    for runtime_response in runtime_responses:
        if isinstance(runtime_response, FailedRuntimeResponse):
            failed_runtime_responses[runtime_response.runtime_request.request_id] = (
                runtime_response
            )
        else:
            response = Response(
                http_response=runtime_response.http_response,
                runtime_request=runtime_response.runtime_request,
            )
            responses[runtime_response.runtime_request.request_id] = response
    return responses, failed_request_validations, failed_runtime_responses


async def dispatch_request_group(
    request_group: RequestGroup,
    schema_manager: SchemaManagerProtocol,
    cache_manager: CacheManagerProtocol,
    authentication_headers: dict[int, dict[str, str]],
    requests_per: float = 100.0,
    time_period: float = 60.0,
) -> tuple[
    ResponseGroup,
    dict[UUID, FailedRequestValidation],
    dict[UUID, FailedRuntimeResponse],
]:
    responses, failed_validations, failed_responses = await dispatch_requests(
        requests=request_group.requests,
        schema_manager=schema_manager,
        cache_manager=cache_manager,
        authentication_headers=authentication_headers,
        requests_per=requests_per,
        time_period=time_period,
    )
    response_group = ResponseGroup(group_id=request_group.group_id, responses=responses)
    return response_group, failed_validations, failed_responses
