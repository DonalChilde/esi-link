"""Function for dispatching requests."""

import asyncio
from uuid import UUID

from aiolimiter import AsyncLimiter

from esi_link.esi_auth.models import ResponseGroup
from esi_link.rewrite.actions.response_action import do_response_action
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
from esi_link.rewrite.response.models import Response
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


async def dispatch_requests(
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
        ) -> RuntimeResponse | FailedRuntimeResponse:
            response = await execute_http_request(
                request=request,
                session=async_session,
                cache_manager=web_cache,
                rate_limiter=rate_limiter,
            )
            for action in request.actions:
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
    schema_cache: SchemaCache,
    web_cache: CacheManagerProtocol,
    token_store: TokenStore | None = None,
    requests_per: float = 100.0,
    time_period: float = 60.0,
) -> tuple[
    ResponseGroup,
    dict[UUID, FailedRequestValidation],
    dict[UUID, FailedRuntimeResponse],
]:
    responses, failed_validations, failed_responses = await dispatch_requests(
        requests=request_group.requests,
        schema_cache=schema_cache,
        web_cache=web_cache,
        token_store=token_store,
        requests_per=requests_per,
        time_period=time_period,
    )
    response_group = ResponseGroup(group_id=request_group.group_id, responses=responses)
    return response_group, failed_validations, failed_responses
