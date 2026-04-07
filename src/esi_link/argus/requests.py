"""Requests for fetching esi data to argus."""

import logging
from collections.abc import Iterable
from uuid import uuid4

from esi_link import EsiLink, request_factory
from esi_link.argus.models import (
    GetCorporationsCorporationIdIndustryJobs,
    PostUniverseNames,
)
from esi_link.helpers.make_response_data import make_response_data
from esi_link.models_and_protocols import RequestGroup
from esi_link.type_defs import Lang

logger = logging.getLogger(__name__)


async def corporation_jobs(
    corporation_id: int,
    character_id: int,
    esi_link: EsiLink,
    include_completed: bool = False,
    lang: Lang = "en",
) -> GetCorporationsCorporationIdIndustryJobs:
    """Fetches the corporation's industry jobs from the ESI API.

    Args:
        corporation_id: The ID of the corporation to fetch jobs for.
        character_id: The ID of the character to use for authentication.
        esi_link: An instance of EsiLink to use for API calls.
        include_completed: Whether to include completed jobs in the response. Defaults to False.
        lang: The language to use for the API response. Defaults to "en".

    Returns:
        A GetCorporationsCorporationIdIndustryJobs instance containing the corporation's industry jobs.

    Raises:
        ValueError: If the API call fails or returns a non-200 status code.
    """
    request = request_factory.corporation_jobs(
        corporation_id=corporation_id,
        character_id=character_id,
        include_completed=include_completed,
        lang=lang,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    response_group = await esi_link.do_requests(request_group)
    response = response_group.responses[request.request_id]
    if response.http_response is None or response.http_response.status_code > 399:
        status_code = (
            response.http_response.status_code
            if response.http_response
            else "No response"
        )
        status_text = (
            response.http_response.body_text
            if response.http_response
            else "No response"
        )
        raise ValueError(
            f"Failed to get corporation jobs for corporation ID {corporation_id}. Response status code: {status_code}, Response body: {status_text}"
        )
    rd = make_response_data(response=response)
    jobs = GetCorporationsCorporationIdIndustryJobs.from_response_data(response_data=rd)
    return jobs


async def names_from_ids(ids_: Iterable[int], esi_link: EsiLink) -> PostUniverseNames:
    """Given an iterable of IDs, returns a dictionary mapping each ID to its name.

    Args:
        ids_: An iterable of IDs to look up.
        esi_link: An instance of EsiLink to use for API calls.

    Returns:
        A PostUniverseNames instance containing the resolved names.

    Raises:
        ValueError: If the API call fails or returns a non-200 status code.
    """
    request = request_factory.names_from_ids(ids_=list(ids_))
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    response_group = await esi_link.do_requests(request_group)
    response = response_group.responses[request.request_id]
    if response.http_response is None or response.http_response.status_code > 399:
        status_code = (
            response.http_response.status_code
            if response.http_response
            else "No response"
        )
        status_text = (
            response.http_response.body_text
            if response.http_response
            else "No response"
        )
        logger.error(
            "Failed to get names for IDs. %s", response.model_dump_json(indent=2)
        )
        raise ValueError(
            f"Failed to get names for IDs {ids_}. error messages: {response.network_exception_messages}"
        )
    rd = make_response_data(response=response)
    names = PostUniverseNames.from_response_data(response_data=rd)
    return names
