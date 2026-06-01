"""This module contains functions for generating RuntimeRequest and RuntimeRequestGroup objects."""

import logging
from copy import deepcopy
from dataclasses import replace
from uuid import UUID, uuid5

from httpx2 import Client

from esi_link import ESI_LINK_NAMESPACE
from esi_link.rewrite.auth.token_store import TokenStore
from esi_link.rewrite.helpers.canonicalize_url import combine_and_canonicalize_url
from esi_link.rewrite.runtime.models import (
    InvalidRuntimeRequest,
    RuntimeGroupMetrics,
    RuntimeRequest,
    RuntimeRequestGroup,
)
from esi_link.rewrite.validation.models import (
    ValidatedRequest,
    ValidatedRequestGroup,
)

logger = logging.getLogger(__name__)


def generate_runtime_request(
    validated_request: ValidatedRequest,
    token_store: TokenStore | None,
    session: Client,
    timeout_seconds: int = 10,
) -> RuntimeRequest | InvalidRuntimeRequest:
    """Generate a RuntimeRequest from a ValidatedRequest and the corresponding EsiSchema."""
    in_process = RuntimeRequest(
        request_id=validated_request.request_id, timeout=timeout_seconds
    )
    in_process = _set_path_url(validated_request, in_process)
    in_process = _set_cache_url(validated_request, in_process)
    in_process = _set_cache_key(validated_request, in_process)
    in_process = _set_headers(
        validated_request, in_process, token_store=token_store, session=session
    )
    in_process = _set_additional_query_parameters(validated_request, in_process)
    return in_process


def generate_runtime_request_group(
    validated_request_group: ValidatedRequestGroup,
    token_store: TokenStore | None,
    session: Client,
    timeout_seconds: int = 10,
) -> RuntimeRequestGroup:
    """Generate a RuntimeRequestGroup from a ValidatedRequestGroup."""
    runtime_requests: dict[UUID, RuntimeRequest] = {}
    invalid_runtime_requests: dict[UUID, InvalidRuntimeRequest] = {}
    for request_id, validated_request in validated_request_group.valid_requests.items():
        runtime_request = generate_runtime_request(
            validated_request=validated_request,
            token_store=token_store,
            session=session,
            timeout_seconds=timeout_seconds,
        )
        if isinstance(runtime_request, InvalidRuntimeRequest):
            invalid_runtime_requests[request_id] = runtime_request
        else:
            runtime_requests[request_id] = runtime_request
    runtime_group = RuntimeRequestGroup(
        request_group=validated_request_group.request_group,
        validated_requests=validated_request_group.valid_requests,
        invalid_requests=validated_request_group.invalid_requests,
        validated_actions=validated_request_group.valid_actions,
        invalid_actions=validated_request_group.invalid_actions,
        runtime_requests=runtime_requests,
        invalid_runtime_requests=invalid_runtime_requests,
        metrics=RuntimeGroupMetrics(),
    )
    return runtime_group


def _set_path_url(
    validated_request: ValidatedRequest,
    inprocess_request: RuntimeRequest,
) -> RuntimeRequest:
    """Sets the resolved_path_url field of the RuntimeRequest based on the URL template and path parameters."""
    if not validated_request.path_parameters:
        path_url = validated_request.path_url_template
    else:
        # template = Template(inprocess_request.path_url_template)
        try:
            path_url = validated_request.path_url_template.format(
                **validated_request.path_parameters
            )
        except KeyError as e:
            logger.error(
                "Missing path parameter for URL template substitution. url_template=%s, path_parameters=%r",
                validated_request.path_url_template,
                validated_request.path_parameters,
            )
            raise ValueError(
                f"Missing path parameter for URL template substitution. {e}"
            ) from e
    # Update the inprocess_request with the generated resolved_path_url
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(inprocess_request, resolved_path_url=path_url)
    return inprocess_request


def _set_cache_url(
    validated_request: ValidatedRequest,
    inprocess_request: RuntimeRequest,
) -> RuntimeRequest:
    """Sets the cache_url field of the RuntimeRequest based on the path_url and query parameters."""
    if not inprocess_request.resolved_path_url:
        raise ValueError(
            "Cannot set cache_url because path_url is not set. Ensure that _set_path_url is called before _set_cache_url."
        )
    if not validated_request.is_cached:
        # If the request is not for a cached endpoint, we can skip generating the cache_url
        # and just return the inprocess_request.
        return deepcopy(inprocess_request)
    path_url = inprocess_request.resolved_path_url
    # NOTE: the `page` query parameter is removed during validation since pagination is
    # handled separately in the runtime logic, so we don't need to worry about it here.
    query_parameters = validated_request.query_parameters or {}
    cache_url = combine_and_canonicalize_url(path_url, query_parameters)
    # Update the inprocess_request with the generated cache_url
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(inprocess_request, cache_url=cache_url)
    return inprocess_request


def _set_cache_key(
    validated_request: ValidatedRequest,
    inprocess_request: RuntimeRequest,
) -> RuntimeRequest:
    """Sets the cache_key field of the RuntimeRequest based on the cache_url."""
    if not inprocess_request.cache_url:
        return deepcopy(inprocess_request)
    cache_url = inprocess_request.cache_url
    x_compatibility_date = validated_request.x_compatibility_date
    # Incorporate the x_compatibility_date into the cache key generation to ensure that
    # cache keys are invalidated when the compatibility date **for the route** changes,
    # which typically indicates a schema change that could affect the structure of the
    # response data.
    cache_url_with_compat = f"{cache_url}|{x_compatibility_date}"
    # Generate a UUID5 hash of the cache_url using the ESI_LINK_NAMESPACE
    cache_key = uuid5(ESI_LINK_NAMESPACE, cache_url_with_compat)
    # Update the inprocess_request with the generated cache_key
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(inprocess_request, cache_key=cache_key)
    return inprocess_request


def _set_headers(
    validated_request: ValidatedRequest,
    inprocess_request: RuntimeRequest,
    *,
    token_store: TokenStore | None,
    session: Client,
) -> RuntimeRequest:
    """Sets the headers field of the RuntimeRequest based on the authentication requirements of the request and the provided authorization headers."""
    headers: dict[str, str] = {}
    if validated_request.is_authentication_required:
        if validated_request.authorization_id is None:
            raise ValueError(
                "Request requires authentication but no authorization_id is provided in the request."
            )
        if token_store is None:
            raise ValueError(
                "Request requires authentication but no token_store is provided."
            )
        try:
            authorization_header = token_store.refresh_character_token(
                validated_request.authorization_id, session=session
            ).auth_headers
        except Exception as e:
            raise ValueError(
                f"Request requires authentication but authentication header is not available "
                f"for the given authorization_id {validated_request.authorization_id}."
            ) from e
        headers.update(authorization_header)
    headers["Accept-Language"] = validated_request.language
    headers["X-Compatibility-Date"] = validated_request.compatibility_date

    # Update the inprocess_request with the generated headers
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(inprocess_request, headers=headers)
    return inprocess_request


def _set_additional_query_parameters(
    validated_request: ValidatedRequest,
    inprocess_request: RuntimeRequest,
) -> RuntimeRequest:
    additional_query_params = (
        deepcopy(inprocess_request.additional_query_parameters) or {}
    )
    if validated_request.is_paged:
        additional_query_params["page"] = 1
    # Update the inprocess_request with the generated query parameters
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(
        inprocess_request, additional_query_parameters=additional_query_params
    )
    return inprocess_request
