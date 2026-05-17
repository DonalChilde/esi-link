import asyncio
from uuid import UUID

import aiohttp
from aiolimiter import AsyncLimiter
from whenever import Instant

from esi_link import USER_AGENT
from esi_link.request_validation import validate_request_group
from esi_link.runtime_request import generate_runtime_request_group
from esi_link.simplified_models import (
    FailedRequestGroupValidation,
    FailedRequestValidation,
    FailedRuntimeResponse,
    RequestGroup,
    Response,
    ResponseGroup,
)
from esi_link.simplified_protocols import CacheManagerProtocol, SchemaManagerProtocol
from esi_link.simplified_request_executor import execute_request_with_cache


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
    """Dispatch a request group and return the combined response."""
    if not request_group.requests:
        raise ValueError("Request group must contain at least one request.")
    validated_request_group = validate_request_group(
        request_group,
        schema_manager,
        authorized_characters=set(authentication_headers.keys()),
    )
    if isinstance(validated_request_group, FailedRequestGroupValidation):
        raise ValueError(
            f"Request group validation failed: {validated_request_group.errors}"
        )
    failed_request_validations: dict[UUID, FailedRequestValidation] = (
        validated_request_group.failed_request_validations
    )
    failed_runtime_responses: dict[UUID, FailedRuntimeResponse] = {}
    runtime_request_group = generate_runtime_request_group(
        validated_request_group, authentication_headers, USER_AGENT
    )
    runtime_request_group.metrics.group_execution_started = Instant.now()
    async with aiohttp.ClientSession() as session:
        rate_limiter = AsyncLimiter(requests_per, time_period)
        tasks = [
            execute_request_with_cache(
                request=request,
                session=session,
                cache_manager=cache_manager,
                rate_limiter=rate_limiter,
            )
            for request in runtime_request_group.requests.values()
        ]
        runtime_responses = await asyncio.gather(*tasks)
        runtime_request_group.metrics.group_execution_completed = Instant.now()
        response_group = ResponseGroup(
            group_id=runtime_request_group.group_id,
            description=runtime_request_group.description,
            save_directory_template=runtime_request_group.save_directory_template,
            save_filename_template=runtime_request_group.save_filename_template,
            metrics=runtime_request_group.metrics,
        )
        for runtime_response in runtime_responses:
            if isinstance(runtime_response, FailedRuntimeResponse):
                failed_runtime_responses[
                    runtime_response.runtime_request.request_id
                ] = runtime_response
            else:
                response = Response(
                    http_response=runtime_response.http_response,
                    runtime_request=runtime_response.runtime_request,
                )
                response_group.responses[
                    runtime_response.runtime_request.request_id
                ] = response
    return response_group, failed_request_validations, failed_runtime_responses
