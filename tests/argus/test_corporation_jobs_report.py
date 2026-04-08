"""Tests for corporation jobs markdown report generation."""

from esi_link.argus.models import GetCorporationsCorporationIdIndustryJobsItem
from esi_link.argus.reports.corporation_jobs import (
    CorporationJobsResolved,
    CorporationJobsResolvedItem,
    generate_corporation_jobs_report,
)


def _job_item(
    *,
    activity_id: int,
    installer_id: int,
    status: str,
    end_date: str,
    completed_date: str | None = None,
) -> GetCorporationsCorporationIdIndustryJobsItem:
    """Create a minimal industry job item for report tests."""
    return GetCorporationsCorporationIdIndustryJobsItem(
        activity_id=activity_id,
        blueprint_id=1,
        blueprint_location_id=60003760,
        blueprint_type_id=34,
        completed_character_id=None,
        completed_date=completed_date,
        cost=None,
        duration=3600,
        end_date=end_date,
        facility_id=1028858195912,
        installer_id=installer_id,
        job_id=installer_id * 100 + activity_id,
        licensed_runs=None,
        location_id=1028858195912,
        output_location_id=1028858195912,
        pause_date=None,
        probability=None,
        product_type_id=35,
        runs=1,
        start_date="2026-04-07T00:00:00Z",
        status=status,
        successful_runs=None,
    )


def test_generate_corporation_jobs_report_includes_summary_and_job_table() -> None:
    """Report output should include the requested markdown sections and columns."""
    jobs = [
        CorporationJobsResolvedItem(
            activity="MANUFACTURING",
            blueprint="Tritanium",
            blueprint_location="Jita 4-4",
            completed_character=None,
            facility="Tatara",
            installer="Alice",
            location="Jita",
            output_location="Jita",
            product="Pyerite",
            item=_job_item(
                activity_id=1,
                installer_id=90000001,
                status="active",
                end_date="2026-04-08T00:00:00Z",
            ),
        ),
        CorporationJobsResolvedItem(
            activity="REACTIONS",
            blueprint="Reaction Formula",
            blueprint_location="Perimeter",
            completed_character="Bob",
            facility="Athanor",
            installer="Alice",
            location="Perimeter",
            output_location="Perimeter",
            product="Fuel Block",
            item=_job_item(
                activity_id=11,
                installer_id=90000001,
                status="delivered",
                end_date="2026-04-07T01:00:00Z",
                completed_date="2026-04-07T01:30:00Z",
            ),
        ),
    ]

    resolved = CorporationJobsResolved(
        corporation_id=98196252,
        name="Acme Corp",
        date="2026-04-07T00:00:00Z",
        jobs=jobs,
    )

    report = generate_corporation_jobs_report(resolved_jobs=resolved)

    assert "# Corporation Jobs Report - 2026-04-07T00:00:00Z" in report
    assert "## Character Summary" in report
    assert "## Jobs" in report
    assert (
        "| Activity | Blueprint | Facility | Installer | Product | End Date | Status |"
        in report
    )
    assert "2026-04-07T01:00:00Z" in report
    assert "Tue, 07 Apr 2026 01:00:00 GMT" not in report
    assert "| Alice | 1/0/0/1 | 0/0/0/0 | 1/1/0/0 | 2/1/0/1 |" in report
    assert "COMPLETED" in report
