"""Function for dispatching requests."""

import asyncio
from copy import deepcopy
from typing import Any
from uuid import UUID

from aiolimiter import AsyncLimiter

from esi_link.rewrite.actions.response_action import (
    do_response_action,
    get_response_action_instance,
)
from esi_link.rewrite.auth.token_store import TokenStore
from esi_link.rewrite.execution.request_executor_httpx2 import (
    execute_http_request,
)
from esi_link.rewrite.helpers.http_client import (
    config_async_http_client,
    config_http_client,
)
from esi_link.rewrite.protocols.cache_manager import (
    CacheManagerProtocol,
)
from esi_link.rewrite.request.models import (
    Request,
    RequestGroup,
)
from esi_link.rewrite.response.models import Response, ResponseGroup
from esi_link.rewrite.runtime.models import (
    FailedRuntimeResponse,
    RuntimeRequest,
    RuntimeResponse,
)
from esi_link.rewrite.runtime.runtime_request_factory import (
    generate_runtime_request,
)
from esi_link.rewrite.schema.schema_cache import SchemaCache
from esi_link.rewrite.validation.models import FailedRequestValidation
from esi_link.rewrite.validation.request_validation_factory import validate_requests

# TODO refactor web cache name.


async def _dispatch_requests(
    requests: dict[UUID, Request],
    schema_cache: SchemaCache,
    web_cache: CacheManagerProtocol,
    token_store: TokenStore | None = None,
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
    session = config_http_client()
    with session:
        valid_requests, failed_request_validations = validate_requests(
            requests=requests,
            schema_cache=schema_cache,
            session=session,
            token_store=token_store,
        )
        runtime_requests: dict[UUID, RuntimeRequest] = {}
        for request_id, validated_request in valid_requests.items():
            runtime_request = generate_runtime_request(
                validated_request=validated_request,
                token_store=token_store,
                session=session,
            )
            runtime_requests[request_id] = runtime_request
    async_session = await config_async_http_client()
    rate_limiter = AsyncLimiter(requests_per, time_period)
    async with async_session:

        async def execute_with_actions(
            request: RuntimeRequest,
        ) -> Response | FailedRuntimeResponse:
            runtime_response = await execute_http_request(
                request=request,
                session=async_session,
                cache_manager=web_cache,
                rate_limiter=rate_limiter,
            )
            assert runtime_response.http_response is not None, (
                "HTTP response should not be None for successful runtime responses."
            )
            response = Response(
                http_response=runtime_response.http_response,
                runtime_request=runtime_response.runtime_request,
            )
            context: dict[str, Any] = {}
            validated_actions = response.runtime_request.validated_request.actions

            for action in validated_actions:
                # NOTE action might modify the response, so we need to update the response variable with the result of the action.
                action_instance = get_response_action_instance(action)
                response, context = await do_response_action(
                    action=action_instance, response=response, context=context
                )
            return response

        tasks = [
            execute_with_actions(request=request)
            for request in runtime_requests.values()
        ]
        response_list = await asyncio.gather(*tasks)
    responses: dict[UUID, Response] = {}
    failed_runtime_responses: dict[UUID, FailedRuntimeResponse] = {}
    for response in response_list:
        if isinstance(response, FailedRuntimeResponse):
            failed_runtime_responses[response.runtime_request.request_id] = response
        else:
            response = Response(
                http_response=response.http_response,
                runtime_request=response.runtime_request,
            )
            responses[response.runtime_request.request_id] = response
    return responses, failed_request_validations, failed_runtime_responses


async def dispatch_request(
    request: Request,
    schema_cache: SchemaCache,
    web_cache: CacheManagerProtocol,
    token_store: TokenStore | None = None,
    requests_per: float = 100.0,
    time_period: float = 60.0,
) -> Response | FailedRuntimeResponse | FailedRequestValidation:
    """Dispatch a single request and return the response."""
    responses, failed_validations, failed_responses = await _dispatch_requests(
        requests={request.request_id: request},
        schema_cache=schema_cache,
        web_cache=web_cache,
        token_store=token_store,
        requests_per=requests_per,
        time_period=time_period,
    )

    if responses:
        return responses[request.request_id]
    elif failed_validations:
        return failed_validations[request.request_id]
    elif failed_responses:
        return failed_responses[request.request_id]
    else:
        raise RuntimeError(
            "Unexpected error: no response, failed validation, or failed response returned."
        )


async def dispatch_request_group(
    request_group: RequestGroup,
    schema_cache: SchemaCache,
    web_cache: CacheManagerProtocol,
    token_store: TokenStore | None = None,
    requests_per: float = 100.0,
    time_period: float = 60.0,
) -> ResponseGroup:
    """Dispatch a group of requests and return a group of responses."""
    responses, failed_validations, failed_responses = await _dispatch_requests(
        requests=request_group.requests,
        schema_cache=schema_cache,
        web_cache=web_cache,
        token_store=token_store,
        requests_per=requests_per,
        time_period=time_period,
    )
    response_group = ResponseGroup(
        group_id=request_group.group_id,
        created_on=request_group.created_on,
        description=request_group.description,
        group_actions=deepcopy(request_group.group_actions),
        responses=responses,
        failed_request_validations=failed_validations,
        failed_runtime_responses=failed_responses,
    )
    # TODO handle validated group flow?
    # make an internal group for single actions? Then refactor to use group in execution flow. This makes Sense.
    return response_group
