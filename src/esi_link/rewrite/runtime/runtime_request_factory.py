"""This module contains functions for generating RuntimeRequest and RuntimeRequestGroup objects."""

import logging
from copy import deepcopy
from dataclasses import asdict, replace
from uuid import UUID, uuid5

from httpx2 import Client

from esi_link import ESI_LINK_NAMESPACE
from esi_link.rewrite.auth.token_store import TokenStore
from esi_link.rewrite.helpers.canonicalize_url import combine_and_canonicalize_url
from esi_link.rewrite.runtime.models import (
    RequestGroupMetrics,
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
) -> RuntimeRequest:
    """Generate a RuntimeRequest from a ValidatedRequest and the corresponding EsiSchema."""
    validated_dict = asdict(validated_request)
    in_process = RuntimeRequest(**validated_dict, timeout=timeout_seconds)
    in_process = _set_path_url(in_process)
    in_process = _set_cache_url(in_process)
    in_process = _set_cache_key(in_process)
    in_process = _set_headers(in_process, token_store=token_store, session=session)
    in_process = _set_additional_query_parameters(in_process)
    return in_process


def generate_runtime_request_group(
    validated_request_group: ValidatedRequestGroup,
    token_store: TokenStore | None,
    session: Client,
    timeout_seconds: int = 10,
) -> RuntimeRequestGroup:
    """Generate a RuntimeRequestGroup from a ValidatedRequestGroup."""
    runtime_requests: dict[UUID, RuntimeRequest] = {}
    for request_id, validated_request in validated_request_group.requests.items():
        runtime_request = generate_runtime_request(
            validated_request=validated_request,
            token_store=token_store,
            session=session,
            timeout_seconds=timeout_seconds,
        )
        runtime_requests[request_id] = runtime_request
    runtime_group = RuntimeRequestGroup(
        group_id=validated_request_group.group_id,
        created_on=validated_request_group.created_on,
        description=validated_request_group.description,
        # save_directory_template=validated_request_group.save_directory_template,
        # save_filename_template=validated_request_group.save_filename_template,
        requests=runtime_requests,
        metrics=RequestGroupMetrics(),
    )
    return runtime_group


def _set_path_url(
    inprocess_request: RuntimeRequest,
) -> RuntimeRequest:
    """Sets the path_url field of the RuntimeRequest based on the URL template and path parameters."""
    if not inprocess_request.path_parameters:
        path_url = inprocess_request.path_url_template
    else:
        # template = Template(inprocess_request.path_url_template)
        try:
            path_url = inprocess_request.path_url_template.format(
                **inprocess_request.path_parameters
            )
        except KeyError as e:
            logger.error(
                "Missing path parameter for URL template substitution. url_template=%s, path_parameters=%r",
                inprocess_request.path_url_template,
                inprocess_request.path_parameters,
            )
            raise ValueError(
                f"Missing path parameter for URL template substitution. {e}"
            ) from e
    # Update the inprocess_request with the generated path_url
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(inprocess_request, path_url=path_url)
    return inprocess_request


def _set_cache_url(
    inprocess_request: RuntimeRequest,
) -> RuntimeRequest:
    """Sets the cache_url field of the RuntimeRequest based on the path_url and query parameters."""
    if not inprocess_request.path_url:
        raise ValueError(
            "Cannot set cache_url because path_url is not set. Ensure that _set_path_url is called before _set_cache_url."
        )
    if not inprocess_request.is_cached:
        # If the request is not for a cached endpoint, we can skip generating the cache_url
        # and just return the inprocess_request.
        return deepcopy(inprocess_request)
    path_url = inprocess_request.path_url
    # NOTE: the `page` query parameter is removed during validation since pagination is
    # handled separately in the runtime logic, so we don't need to worry about it here.
    query_parameters = inprocess_request.query_parameters or {}
    cache_url = combine_and_canonicalize_url(path_url, query_parameters)
    # Update the inprocess_request with the generated cache_url
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(inprocess_request, cache_url=cache_url)
    return inprocess_request


def _set_cache_key(
    inprocess_request: RuntimeRequest,
) -> RuntimeRequest:
    """Sets the cache_key field of the RuntimeRequest based on the cache_url."""
    if not inprocess_request.cache_url:
        return deepcopy(inprocess_request)
    cache_url = inprocess_request.cache_url
    # Generate a UUID5 hash of the cache_url using the ESI_LINK_NAMESPACE
    cache_key = uuid5(ESI_LINK_NAMESPACE, cache_url)
    # Update the inprocess_request with the generated cache_key
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(inprocess_request, cache_key=cache_key)
    return inprocess_request


def _set_headers(
    inprocess_request: RuntimeRequest,
    token_store: TokenStore | None,
    session: Client,
) -> RuntimeRequest:
    """Sets the headers field of the RuntimeRequest based on the authentication requirements of the request and the provided authorization headers."""
    headers: dict[str, str] = {}
    if inprocess_request.is_authentication_required:
        if inprocess_request.authorization_id is None:
            raise ValueError(
                "Request requires authentication but no authorization_id is provided in the request."
            )
        if token_store is None:
            raise ValueError(
                "Request requires authentication but no token_store is provided."
            )
        try:
            authorization_header = token_store.refresh_character_token(
                inprocess_request.authorization_id, session=session
            ).auth_headers
        except Exception as e:
            raise ValueError(
                f"Request requires authentication but authentication header is not available "
                f"for the given authorization_id {inprocess_request.authorization_id}."
            ) from e
        headers.update(authorization_header)
    headers["Accept-Language"] = inprocess_request.language
    headers["X-Compatibility-Date"] = inprocess_request.compatibility_date

    # Update the inprocess_request with the generated headers
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(inprocess_request, headers=headers)
    return inprocess_request


def _set_additional_query_parameters(
    inprocess_request: RuntimeRequest,
) -> RuntimeRequest:
    additional_query_params = (
        deepcopy(inprocess_request.additional_query_parameters) or {}
    )
    if inprocess_request.is_paged:
        additional_query_params["page"] = 1
    # Update the inprocess_request with the generated query parameters
    inprocess_request = deepcopy(inprocess_request)
    inprocess_request = replace(
        inprocess_request, additional_query_parameters=additional_query_params
    )
    return inprocess_request
