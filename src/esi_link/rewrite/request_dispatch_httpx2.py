"""Function for dispatching requests."""

import asyncio
from uuid import UUID, uuid4

from aiolimiter import AsyncLimiter

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
from esi_link.rewrite.response.models import FailedResponse, Response, ResponseGroup
from esi_link.rewrite.runtime.models import (
    FailedRuntimeResponse,
    RuntimeRequest,
    RuntimeRequestGroup,
    RuntimeResponse,
    RuntimeResponseGroup,
)
from esi_link.rewrite.runtime.runtime_request_factory import (
    generate_runtime_request_group,
)
from esi_link.rewrite.schema.schema_cache import SchemaCache
from esi_link.rewrite.validation.request_validation_factory import (
    validate_request_group,
    # validate_requests,
)

# TODO refactor web cache name.


# async def _dispatch_requests(
#     requests: dict[UUID, Request],
#     schema_cache: SchemaCache,
#     web_cache: CacheManagerProtocol,
#     token_store: TokenStore | None = None,
#     requests_per: float = 100.0,
#     time_period: float = 60.0,
# ) -> tuple[
#     dict[UUID, Response],
#     dict[UUID, InvalidRequest],
#     dict[UUID, FailedRuntimeResponse],
# ]:
#     """Dispatch requests and return the responses."""
#     if not requests:
#         raise ValueError("Requests must contain at least one request.")
#     session = config_http_client()
#     with session:
#         valid_requests, failed_request_validations = validate_requests(
#             requests=requests,
#             schema_cache=schema_cache,
#             session=session,
#             token_store=token_store,
#         )
#         runtime_requests: dict[UUID, RuntimeRequest] = {}
#         for request_id, validated_request in valid_requests.items():
#             runtime_request = generate_runtime_request(
#                 validated_request=validated_request,
#                 token_store=token_store,
#                 session=session,
#             )
#             runtime_requests[request_id] = runtime_request
#     async_session = await config_async_http_client()
#     rate_limiter = AsyncLimiter(requests_per, time_period)
#     async with async_session:

#         async def execute_with_actions(
#             request: RuntimeRequest,
#         ) -> Response | FailedRuntimeResponse:
#             runtime_response = await execute_http_request(
#                 request=request,
#                 session=async_session,
#                 cache_manager=web_cache,
#                 rate_limiter=rate_limiter,
#             )
#             assert runtime_response.http_response is not None, (
#                 "HTTP response should not be None for successful runtime responses."
#             )
#             response = Response(
#                 http_response=runtime_response.http_response,
#                 runtime_request=runtime_response.runtime_request,
#             )
#             context: dict[str, Any] = {}
#             validated_actions = response.runtime_request.validated_request.actions

#             for action in validated_actions:
#                 # NOTE action might modify the response, so we need to update the response variable with the result of the action.
#                 action_instance = get_response_action_instance(action)
#                 response, context = await do_response_action(
#                     action=action_instance, response=response, context=context
#                 )
#             return response

#         tasks = [
#             execute_with_actions(request=request)
#             for request in runtime_requests.values()
#         ]
#         response_list = await asyncio.gather(*tasks)
#     responses: dict[UUID, Response] = {}
#     failed_runtime_responses: dict[UUID, FailedRuntimeResponse] = {}
#     for response in response_list:
#         if isinstance(response, FailedRuntimeResponse):
#             failed_runtime_responses[response.runtime_request.request_id] = response
#         else:
#             response = Response(
#                 http_response=response.http_response,
#                 runtime_request=response.runtime_request,
#             )
#             responses[response.runtime_request.request_id] = response
#     return responses, failed_request_validations, failed_runtime_responses


async def dispatch_request(
    request: Request,
    schema_cache: SchemaCache,
    web_cache: CacheManagerProtocol,
    token_store: TokenStore | None = None,
    requests_per: float = 100.0,
    time_period: float = 60.0,
) -> ResponseGroup:
    """Dispatch a single request and return the response."""
    request_group = RequestGroup(
        group_id=request.request_id,
        created_on=request.created_on,
        description="Single request group",
        requests={request.request_id: request},
        group_actions=[],
    )
    response_group = await dispatch_request_group(
        request_group=request_group,
        schema_cache=schema_cache,
        web_cache=web_cache,
        token_store=token_store,
        requests_per=requests_per,
        time_period=time_period,
    )

    return response_group


async def dispatch_request_group(
    request_group: RequestGroup,
    schema_cache: SchemaCache,
    web_cache: CacheManagerProtocol,
    token_store: TokenStore | None = None,
    timeout_seconds: int = 10,
    requests_per: float = 100.0,
    time_period: float = 60.0,
) -> ResponseGroup:
    """Dispatch a group of requests and return a group of responses."""
    session = config_http_client()
    with session:
        validated_group = validate_request_group(
            request_group=request_group,
            schema_cache=schema_cache,
            session=session,
            token_store=token_store,
        )
        # if isinstance(validated_group, InvalidRequestGroup):
        #     # If the entire group is invalid, we can return early with the failed validation results.
        #     # FIXME This is not the return we want. More thought on failure at this point is needed.
        #     response_group = ResponseGroup(
        #         group_id=request_group.group_id,
        #         created_on=request_group.created_on,
        #         description=request_group.description,
        #         group_actions=deepcopy(request_group.group_actions),
        #         responses={},
        #         # failed_request_validations=validated_group.invalid_requests,
        #         failed_runtime_responses={},
        #     )
        #     return response_group
        runtime_request_group = generate_runtime_request_group(
            validated_request_group=validated_group,
            token_store=token_store,
            session=session,
            timeout_seconds=timeout_seconds,
        )
    async_session = await config_async_http_client()
    rate_limiter = AsyncLimiter(requests_per, time_period)
    async with async_session:

        async def execute_with_actions(
            request: RuntimeRequest,
        ) -> RuntimeResponse | FailedRuntimeResponse:
            runtime_response = await execute_http_request(
                request=request,
                session=async_session,
                cache_manager=web_cache,
                rate_limiter=rate_limiter,
            )
            assert runtime_response.http_response is not None, (
                "HTTP response should not be None for successful runtime responses."
            )

            # FIXME Actions need more thought.

            # context: dict[str, Any] = {}

            # for action in request.validated_actions:
            #     # NOTE action might modify the response, so we need to update the response variable with the result of the action.
            #     action_instance = get_response_action_instance(action)
            #     response, context = await do_response_action(
            #         action=action_instance, response=response, context=context
            #     )
            return runtime_response

        tasks = [
            execute_with_actions(request=request)
            for request in runtime_request_group.runtime_requests.values()
        ]
        response_list = await asyncio.gather(*tasks)

    response_group = _to_response_group(
        runtime_request_group=runtime_request_group,
        response_list=response_list,
    )
    # TODO handle validated group flow?
    # make an internal group for single actions? Then refactor to use group in execution flow. This makes Sense.
    return response_group


def _to_runtime_response_group(
    runtime_request_group: RuntimeRequestGroup,
    response_list: list[RuntimeResponse | FailedRuntimeResponse],
) -> RuntimeResponseGroup:
    """Convert a response group to a dict of runtime responses."""
    runtime_responses: dict[UUID, RuntimeResponse] = {}
    failed_runtime_responses: dict[UUID, FailedRuntimeResponse] = {}
    for response in response_list:
        if isinstance(response, FailedRuntimeResponse):
            failed_runtime_responses[response.runtime_request.request_id] = response
        else:
            runtime_responses[response.runtime_request.request_id] = response
    runtime_response_group = RuntimeResponseGroup(
        request_group=runtime_request_group.request_group,
        valid_requests=runtime_request_group.validated_requests,
        invalid_requests=runtime_request_group.invalid_requests,
        valid_actions=runtime_request_group.validated_actions,
        invalid_actions=runtime_request_group.invalid_actions,
        runtime_requests=runtime_request_group.runtime_requests,
        invalid_runtime_requests=runtime_request_group.invalid_runtime_requests,
        runtime_responses=runtime_responses,
        failed_runtime_responses=failed_runtime_responses,
    )
    return runtime_response_group


def _to_response_group(
    runtime_request_group: RuntimeRequestGroup,
    response_list: list[RuntimeResponse | FailedRuntimeResponse],
) -> ResponseGroup:
    """Convert a runtime response group to a response group."""
    responses: dict[UUID, Response] = {}
    failed_responses: dict[UUID, FailedResponse] = {}
    for response in response_list:
        if isinstance(response, FailedRuntimeResponse):
            failed_responses[response.runtime_request.request_id] = FailedResponse(
                http_response=response.http_response,
                runtime_request=response.runtime_request,
                failure_msg=response.failure_msg,
            )
        else:
            responses[response.runtime_request.request_id] = Response(
                http_response=response.http_response,
                runtime_request=response.runtime_request,
            )
    response_group = ResponseGroup(
        request_group=runtime_request_group.request_group,
        valid_requests=runtime_request_group.validated_requests,
        invalid_requests=runtime_request_group.invalid_requests,
        valid_actions=runtime_request_group.validated_actions,
        invalid_actions=runtime_request_group.invalid_actions,
        runtime_requests=runtime_request_group.runtime_requests,
        invalid_runtime_requests=runtime_request_group.invalid_runtime_requests,
        responses=responses,
        failed_responses=failed_responses,
    )
    return response_group


def _to_response_group_from_runtime_response_group(
    runtime_response_group: RuntimeResponseGroup,
) -> ResponseGroup:
    """Convert a runtime response group to a response group."""
    responses: dict[UUID, Response] = {}
    failed_responses: dict[UUID, FailedResponse] = {}
    for (
        request_id,
        runtime_response,
    ) in runtime_response_group.runtime_responses.items():
        responses[request_id] = Response(
            http_response=runtime_response.http_response,
            runtime_request=runtime_response.runtime_request,
        )
    for (
        request_id,
        failed_runtime_response,
    ) in runtime_response_group.failed_runtime_responses.items():
        failed_responses[request_id] = FailedResponse(
            http_response=failed_runtime_response.http_response,
            runtime_request=failed_runtime_response.runtime_request,
            failure_msg=failed_runtime_response.failure_msg,
        )
    response_group = ResponseGroup(
        request_group=runtime_response_group.request_group,
        valid_requests=runtime_response_group.valid_requests,
        invalid_requests=runtime_response_group.invalid_requests,
        valid_actions=runtime_response_group.valid_actions,
        invalid_actions=runtime_response_group.invalid_actions,
        runtime_requests=runtime_response_group.runtime_requests,
        invalid_runtime_requests=runtime_response_group.invalid_runtime_requests,
        responses=responses,
        failed_responses=failed_responses,
    )
    return response_group
