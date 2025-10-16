import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

from whenever import Instant

from esi_link import esi_link as EL


def test_simple_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a simple EsiLink request and response handling."""

    response_handler = EL.HandlerConfig(
        name="esi-link.json_data_file",
        config={
            "file_path": str(
                test_output_dir / "test_simple_request" / "{operation_id}-response.json"
            )
        },
    )
    esi_request = EL.EsiRequest(
        query_id=uuid4(),
        operation_id="GetStatus",
        handlers=[response_handler],
    )
    esi_schema_data = EL.EsiSchema.from_schema(
        schema=esi_schema, download_date=Instant.now()
    )
    cache = EL.InMemoryCache()
    http_client = EL.EsiHttpRateLimited(cache=cache)
    handler_manager = EL.HandlerManager()
    handler_manager.register_handler(
        EL.JsonFileResponseHandler.name, EL.JsonFileResponseHandler
    )
    esi_link = EL.EsiLink(
        esi_schema=esi_schema_data,
        esi_http=http_client,
        handler_manager=handler_manager,
    )
    ctx = EL.ResponseContext()
    esi_requests = EL.EsiRequests(
        requests={x.query_id: x for x in [esi_request]},
    )
    asyncio.run(esi_link.execute_requests(ctx=ctx, requests=esi_requests))


def test_paged_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a paged EsiLink request and response handling."""

    ...


def test_batched_requests(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test multiple EsiLink requests and response handling."""

    ...


def test_cached_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a cached EsiLink request and response handling."""

    ...


def test_unauthorized_request(
    esi_schema: dict[str, Any], test_output_dir: Path
) -> None:
    """Test an unauthorized EsiLink request and response handling."""

    ...


def test_authenticated_request(
    esi_schema: dict[str, Any], test_output_dir: Path
) -> None:
    """Test an authenticated EsiLink request and response handling."""

    ...


def test_invalid_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test an invalid EsiLink request and response handling."""

    ...


def test_slow_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a slow EsiLink request and response handling."""
    ...


def test_400_status_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a 400 status EsiLink request and response handling."""
    ...


def test_500_status_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a 500 status EsiLink request and response handling."""
    ...


def test_rate_limited_request(
    esi_schema: dict[str, Any], test_output_dir: Path
) -> None:
    """Test a rate limited EsiLink request and response handling."""
    ...
