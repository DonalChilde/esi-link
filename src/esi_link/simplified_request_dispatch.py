"""Function for dispatching requests."""

import asyncio
from uuid import UUID

import aiohttp
from aiolimiter import AsyncLimiter

from esi_link import USER_AGENT
from esi_link.request_validation import validate_request
from esi_link.runtime_request import (
    generate_runtime_request,
)
from esi_link.simplified_models import (
    FailedRequestValidation,
    FailedRuntimeResponse,
    Request,
    Response,
    RuntimeRequest,
    ValidatedRequest,
)
from esi_link.simplified_protocols import CacheManagerProtocol, SchemaManagerProtocol
from esi_link.simplified_request_executor import execute_request_with_cache


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
    """Dispatch a request group and return the combined response."""
    if not requests:
        raise ValueError("Requests must contain at least one request.")
    failed_request_validations: dict[UUID, FailedRequestValidation] = {}
    valid_requests: dict[UUID, ValidatedRequest] = {}
    for request_id, request in requests.items():
        validated_request = validate_request(
            request=request,
            schema_manager=schema_manager,
            authorized_characters=set(authentication_headers.keys()),
        )
        if isinstance(validated_request, FailedRequestValidation):
            failed_request_validations[request_id] = validated_request
        else:
            valid_requests[request_id] = validated_request

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
        tasks = [
            execute_request_with_cache(
                request=request,
                session=session,
                cache_manager=cache_manager,
                rate_limiter=rate_limiter,
            )
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
