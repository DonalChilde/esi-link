"""Requests for fetching esi data to argus."""

import logging
from collections.abc import Iterable
from uuid import uuid4

from esi_link import EsiLink, request_factory
from esi_link.argus import models as argus_models
from esi_link.errors import EsiLinkError
from esi_link.helpers.make_response_data import make_response_data
from esi_link.helpers.raise_for_errors import raise_for_network_errors
from esi_link.models_and_protocols import RequestGroup
from esi_link.type_defs import Lang

logger = logging.getLogger(__name__)

POST_UNIVERSE_NAMES_MAX_ID = 2_147_483_647
"""Maximum ID value accepted by the universe names endpoint in practice.

Although the published schema documents int64 items, ESI rejects large structure and
item IDs returned by corporation industry jobs. Filtering those IDs here prevents the
entire batch from failing when a report mixes resolvable universe IDs with
non-resolvable location identifiers.
"""


def _prepare_post_universe_name_ids(ids_: Iterable[int]) -> tuple[list[int], list[int]]:
    """Filter and deduplicate IDs before calling PostUniverseNames.

    Args:
        ids_: Raw IDs gathered from Argus data models.

    Returns:
        A tuple containing the IDs that are safe to send to PostUniverseNames and the
        IDs filtered out as unsupported.
    """
    valid_ids: list[int] = []
    filtered_ids: list[int] = []
    seen_ids: set[int] = set()

    for id_ in ids_:
        if id_ <= 0:
            continue
        if id_ > POST_UNIVERSE_NAMES_MAX_ID:
            filtered_ids.append(id_)
            continue
        if id_ in seen_ids:
            continue
        seen_ids.add(id_)
        valid_ids.append(id_)

    return valid_ids, filtered_ids


async def corporation_blueprints(
    corporation_id: int, character_id: int, esi_link: EsiLink, lang: Lang = "en"
) -> argus_models.GetCorporationsCorporationIdBlueprints:
    """Fetches the corporation's blueprints from the ESI API.

    Args:
        corporation_id: The ID of the corporation to fetch blueprints for.
        character_id: The ID of the character to use for authentication.
        esi_link: An instance of EsiLink to use for API calls.
        lang: The language to use for the API response. Defaults to "en".

    Returns:
        A GetCorporationsCorporationIdBlueprints instance containing the corporation's blueprints.

    Raises:
        ValueError: If the API call fails or returns a > 399 status code.
    """
    request = request_factory.corporation_blueprints(
        corporation_id=corporation_id,
        character_id=character_id,
        lang=lang,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    response_group = await esi_link.do_requests(request_group)
    response = response_group.responses[request.request_id]
    try:
        raise_for_network_errors(response)
    except EsiLinkError as e:
        logger.error("Network error while fetching corporation blueprints: %s", e)
        raise ValueError(f"Failed to fetch corporation blueprints. {e}") from e

    rd = make_response_data(response=response)
    blueprints = argus_models.GetCorporationsCorporationIdBlueprints.from_response_data(
        response_data=rd
    )
    return blueprints


async def corporation_jobs(
    corporation_id: int,
    character_id: int,
    esi_link: EsiLink,
    include_completed: bool = False,
    lang: Lang = "en",
) -> argus_models.GetCorporationsCorporationIdIndustryJobs:
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
        ValueError: If the API call fails or returns a > 399 status code.
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
    try:
        raise_for_network_errors(response)
    except EsiLinkError as e:
        logger.error("Network error while fetching corporation jobs: %s", e)
        raise ValueError(f"Failed to fetch corporation jobs. {e}") from e
    rd = make_response_data(response=response)
    jobs = argus_models.GetCorporationsCorporationIdIndustryJobs.from_response_data(
        response_data=rd
    )
    return jobs


async def names_from_ids(
    ids_: Iterable[int], esi_link: EsiLink
) -> argus_models.PostUniverseNames:
    """Given an iterable of IDs, returns a dictionary mapping each ID to its name.

    The ESI API has a limit of 1000 IDs per request. This function automatically
    batches requests if needed and merges the results. It also filters out large
    structure and item IDs that the endpoint does not resolve.

    Args:
        ids_: An iterable of IDs to look up.
        esi_link: An instance of EsiLink to use for API calls.

    Returns:
        A PostUniverseNames instance containing the resolved names.

    Raises:
        ValueError: If the API call fails or returns a > 399 status code.
    """
    id_list, filtered_ids = _prepare_post_universe_name_ids(ids_)

    if filtered_ids:
        logger.warning(
            "Skipping %s IDs that PostUniverseNames does not accept. Sample: %s",
            len(filtered_ids),
            filtered_ids[:5],
        )

    if not id_list:
        raise ValueError("No supported IDs available for PostUniverseNames.")

    logger.info("Resolving %s unique IDs to names", len(id_list))

    if len(id_list) > 1000:
        logger.warning(
            "Requested %s IDs, exceeds ESI limit of 1000. Will batch into multiple requests.",
            len(id_list),
        )

    batch_size = 900
    id_batches = [
        id_list[i : i + batch_size] for i in range(0, len(id_list), batch_size)
    ]

    logger.info("Sending %s batch request(s) to ESI", len(id_batches))

    all_names_dict: dict[int, object] = {}
    first_batch_response: argus_models.PostUniverseNames | None = None

    for batch_idx, batch_ids in enumerate(id_batches, 1):
        logger.debug(
            "Processing batch %s/%s with %s IDs",
            batch_idx,
            len(id_batches),
            len(batch_ids),
        )

        request = request_factory.names_from_ids(ids_=batch_ids)
        request_group = RequestGroup(
            group_id=uuid4(), requests={request.request_id: request}
        )
        response_group = await esi_link.do_requests(request_group)
        response = response_group.responses[request.request_id]
        try:
            raise_for_network_errors(response)
        except EsiLinkError as e:
            logger.error("Network error for batch %s: %s", batch_idx, e)
            raise ValueError(f"Failed to resolve names for batch {batch_idx}.") from e

        rd = make_response_data(response=response)
        batch_names = argus_models.PostUniverseNames.from_response_data(
            response_data=rd
        )

        if first_batch_response is None:
            first_batch_response = batch_names

        all_names_dict.update(batch_names.names)
        logger.debug(
            "Batch %s returned %s names",
            batch_idx,
            len(batch_names.names),
        )

    if first_batch_response is None:
        raise ValueError(f"Failed to resolve any IDs. No successful batch responses.")

    names = argus_models.PostUniverseNames.model_validate(
        {
            "operation_id": first_batch_response.operation_id,
            "response_date": first_batch_response.response_date,
            "received_at": first_batch_response.received_at,
            "names": all_names_dict,
        }
    )
    logger.info("Successfully resolved %s unique IDs to names", len(names.names))
    return names


async def character_blueprints(
    character_id: int, esi_link: EsiLink, lang: Lang = "en"
) -> argus_models.GetCorporationsCorporationIdIndustryJobs:
    """Fetches the character's blueprints from the ESI API.

    Args:
        character_id: The ID of the character to fetch blueprints for.
        esi_link: An instance of EsiLink to use for API calls.
        lang: The language to use for the API response. Defaults to "en".

    Returns:
        A GetCorporationsCorporationIdIndustryJobs instance containing the character's blueprints.

    Raises:
        ValueError: If the API call fails or returns a > 399 status code.
    """
    request = request_factory.character_blueprints(
        character_id=character_id,
        lang=lang,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    response_group = await esi_link.do_requests(request_group)
    response = response_group.responses[request.request_id]
    try:
        raise_for_network_errors(response)
    except EsiLinkError as e:
        logger.error("Network error while fetching character blueprints: %s", e)
        raise ValueError(f"Failed to fetch character blueprints. {e}") from e

    rd = make_response_data(response=response)
    blueprints = (
        argus_models.GetCorporationsCorporationIdIndustryJobs.from_response_data(
            response_data=rd
        )
    )
    return blueprints


async def character_information(
    character_id: int, esi_link: EsiLink, lang: Lang = "en"
) -> argus_models.GetCharactersCharacterId:
    """Fetches the character's information from the ESI API.

    Args:
        character_id: The ID of the character to fetch information for.
        esi_link: An instance of EsiLink to use for API calls.
        lang: The language to use for the API response. Defaults to "en".

    Returns:
        A GetCharactersCharacterId instance containing the character's information.

    Raises:
        ValueError: If the API call fails or returns a > 399 status code.
    """
    request = request_factory.character_information(
        character_id=character_id,
        lang=lang,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    response_group = await esi_link.do_requests(request_group)
    response = response_group.responses[request.request_id]
    try:
        raise_for_network_errors(response)
    except EsiLinkError as e:
        logger.error("Network error while fetching character information: %s", e)
        raise ValueError(f"Failed to fetch character information. {e}") from e

    rd = make_response_data(response=response)
    character_info = argus_models.GetCharactersCharacterId.from_response_data(
        response_data=rd
    )
    return character_info


async def character_jobs(
    character_id: int,
    esi_link: EsiLink,
    include_completed: bool = False,
    lang: Lang = "en",
) -> argus_models.GetCharactersCharacterIdIndustryJobs:
    """Fetches the character's industry jobs from the ESI API.

    Args:
        character_id: The ID of the character to fetch jobs for.
        esi_link: An instance of EsiLink to use for API calls.
        include_completed: Whether to include completed jobs in the response. Defaults to False.
        lang: The language to use for the API response. Defaults to "en".

    Returns:
        A GetCharactersCharacterIdIndustryJobs instance containing the character's industry jobs.

    Raises:
        ValueError: If the API call fails or returns a > 399 status code.
    """
    request = request_factory.character_jobs(
        character_id=character_id,
        include_completed=include_completed,
        lang=lang,
    )
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    response_group = await esi_link.do_requests(request_group)
    response = response_group.responses[request.request_id]
    try:
        raise_for_network_errors(response)
    except EsiLinkError as e:
        logger.error("Network error while fetching character jobs: %s", e)
        raise ValueError(f"Failed to fetch character jobs. {e}") from e

    rd = make_response_data(response=response)
    jobs = argus_models.GetCharactersCharacterIdIndustryJobs.from_response_data(
        response_data=rd
    )
    return jobs


async def universe_prices(
    esi_link: EsiLink,
    lang: Lang = "en",
) -> argus_models.GetMarketsPrices:
    """Fetches the universe prices from the ESI API.

    Args:
        esi_link: An instance of EsiLink to use for API calls.
        lang: The language to use for the API response. Defaults to "en".

    Returns:
        A GetMarketsPrices instance containing the universe prices.

    Raises:
        ValueError: If the API call fails or returns a > 399 status code.
    """
    request = request_factory.markets_prices(lang=lang)
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    response_group = await esi_link.do_requests(request_group)
    response = response_group.responses[request.request_id]
    try:
        raise_for_network_errors(response)
    except EsiLinkError as e:
        logger.error("Network error while fetching universe prices: %s", e)
        raise ValueError(f"Failed to fetch universe prices. {e}") from e

    rd = make_response_data(response=response)
    prices = argus_models.GetMarketsPrices.from_response_data(response_data=rd)
    return prices


async def market_orders_region(
    region_id: int,
    esi_link: EsiLink,
    lang: Lang = "en",
) -> argus_models.GetMarketsRegionIdOrders:
    """Fetches the market orders for a region from the ESI API.

    Args:
        region_id: The ID of the region to fetch market orders for.
        esi_link: An instance of EsiLink to use for API calls.
        lang: The language to use for the API response. Defaults to "en".

    Returns:
        A GetMarketsRegionIdOrders instance containing the market orders for the region.

    Raises:
        ValueError: If the API call fails or returns a > 399 status code.
    """
    request = request_factory.market_orders(region_id=region_id, lang=lang)
    request_group = RequestGroup(
        group_id=uuid4(), requests={request.request_id: request}
    )
    response_group = await esi_link.do_requests(request_group)
    response = response_group.responses[request.request_id]
    try:
        raise_for_network_errors(response)
    except EsiLinkError as e:
        logger.error(
            "Network error while fetching market orders for region %s: %s", region_id, e
        )
        raise ValueError(
            f"Failed to fetch market orders for region {region_id}. {e}"
        ) from e

    rd = make_response_data(response=response)
    orders = argus_models.GetMarketsRegionIdOrders.from_response_data(response_data=rd)
    return orders
