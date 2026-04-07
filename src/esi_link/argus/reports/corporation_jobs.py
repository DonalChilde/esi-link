"""Report generation for corporation industry jobs."""

from dataclasses import dataclass

from pydantic import BaseModel
from whenever import Instant

from esi_link import EsiLink
from esi_link.argus import requests
from esi_link.argus.models import (
    GetCorporationsCorporationIdIndustryJobs,
    GetCorporationsCorporationIdIndustryJobsItem,
)


@dataclass(slots=True, kw_only=True)
class CorporationJobsResolvedItem:
    """A resolved item for a corporation's industry job.

    id fields are resolved to their names for easier readability.
    The original item is still available as the `item` attribute for reference.
    Data that is not resolved or transformed is left as-is in the `item` attribute.
    """

    activity: str
    blueprint_location: str
    blueprint: str
    completed_character: str | None
    completed_date: str | None
    """The date the job was completed. This is a string in ISO 8601 format."""
    end_date: str
    """The date the job is expected to be completed. This is a string in ISO 8601 format."""
    facility: str
    installer: str
    location: str
    output_location: str
    pause_date: str | None
    """The date the job was paused. This is a string in ISO 8601 format."""
    product: str | None
    start_date: str
    """The date the job was started. This is a string in ISO 8601 format."""

    item: GetCorporationsCorporationIdIndustryJobsItem


class CorporationJobsResolved(BaseModel):
    corporation_id: int
    name: str
    """The name of the corporation."""
    date: str
    """The date the report was generated. This is a string in ISO 8601 format."""
    jobs: list[CorporationJobsResolvedItem] = []


async def resolve_corporation_jobs(
    corp_jobs: GetCorporationsCorporationIdIndustryJobs, esi_link: EsiLink
) -> CorporationJobsResolved:
    """Generates a report of a corporation's industry jobs.

    Resolves all relevant IDs to their names for easier readability in the report.
    Dates are converted to ISO 8601 format for consistency and easier parsing.

    Args:
        corp_jobs: The corporation's industry jobs data from the ESI API.
        esi_link: An instance of EsiLink to use for API calls.

    Returns:
        A CorporationJobsReport containing the corporation's industry jobs.
    """
    ids_to_resolve = get_ids_from_corporation_jobs(corp_jobs)
    names = await requests.names_from_ids(ids_=ids_to_resolve, esi_link=esi_link)
    report_items: list[CorporationJobsResolvedItem] = []
    for job in corp_jobs.jobs:
        completed_date = (
            Instant.parse_rfc2822(job.completed_date).format_iso()
            if job.completed_date
            else None
        )
        end_date = Instant.parse_rfc2822(job.end_date).format_iso()
        start_date = Instant.parse_rfc2822(job.start_date).format_iso()
        pause_date = (
            Instant.parse_rfc2822(job.pause_date).format_iso()
            if job.pause_date
            else None
        )
        completed_character = (
            names.name(job.completed_character_id)
            if job.completed_character_id
            else None
        )
        report_item = CorporationJobsResolvedItem(
            activity=str(job.activity_id),
            blueprint_location=names.name(job.blueprint_location_id),
            blueprint=names.name(job.blueprint_type_id),
            completed_character=completed_character,
            completed_date=completed_date,
            end_date=end_date,
            facility=names.name(job.facility_id),
            installer=names.name(job.installer_id),
            location=names.name(job.location_id),
            output_location=names.name(job.output_location_id),
            pause_date=pause_date,
            product=names.name(job.product_type_id) if job.product_type_id else None,
            start_date=start_date,
            item=job,
        )
        report_items.append(report_item)
    report = CorporationJobsResolved(
        corporation_id=corp_jobs.corporation_id,
        name=names.name(corp_jobs.corporation_id),
        date=Instant.now().format_iso(),
        jobs=report_items,
    )
    return report


def get_ids_from_corporation_jobs(
    jobs: GetCorporationsCorporationIdIndustryJobs,
) -> set[int]:
    """Extracts all unique IDs from a GetCorporationsCorporationIdIndustryJobs response."""
    ids: set[int] = set()
    ids.add(jobs.corporation_id)
    for job in jobs.jobs:
        ids.add(job.blueprint_location_id)
        ids.add(job.blueprint_type_id)
        if job.completed_character_id is not None:
            ids.add(job.completed_character_id)
        ids.add(job.facility_id)
        ids.add(job.installer_id)
        ids.add(job.location_id)
        ids.add(job.output_location_id)
        if job.product_type_id is not None:
            ids.add(job.product_type_id)
    return ids
