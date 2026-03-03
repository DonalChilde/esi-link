"""Tests for EsiLink EsiRequest execution and response handling."""

import asyncio
import logging
from pathlib import Path
from string import Template
from typing import Any
from uuid import uuid4

from whenever import Instant

from esi_link.cache_p import InMemoryCache
from esi_link.esi_http import EsiHttpRateLimited
from esi_link.esi_link import EsiLink
from esi_link.models import (
    EsiRequest,
    EsiRequests,
    EsiResponse,
    EsiSchema,
    HandlerConfig,
)
from esi_link.response_handlers import EsiResponseToFile, HandlerManager

logger = logging.getLogger(__name__)


def test_simple_get_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a simple EsiLink request and response handling."""
    operation_id = "GetStatus"
    output_path_str = (
        f"{test_output_dir}/test_simple_request/${{OPERATION_ID}}-response.json"
    )
    response_handler = HandlerConfig(
        name="esi-link.esi_response_to_file",
        config={
            "file_path": output_path_str,
            "overwrite": False,
        },
    )

    esi_request = EsiRequest(
        request_id=uuid4(),
        operation_id=operation_id,
        handlers=[response_handler],
    )
    esi_schema_data = EsiSchema.from_schema(
        schema=esi_schema, download_date=Instant.now()
    )
    cache = InMemoryCache()
    http_client = EsiHttpRateLimited(cache=cache, esi_schema=esi_schema_data)
    handler_manager = HandlerManager()
    handler_manager.register_handler(EsiResponseToFile.name, EsiResponseToFile)
    esi_link = EsiLink(
        esi_schema=esi_schema_data,
        esi_http=http_client,
        handler_manager=handler_manager,
    )

    esi_requests = EsiRequests(
        requests_id=uuid4(),
        requests={x.request_id: x for x in [esi_request]},
    )
    asyncio.run(esi_link.execute_requests(requests=esi_requests))
    path_template = Template(output_path_str)
    output_path = Path(path_template.substitute(OPERATION_ID=operation_id))
    assert output_path.is_file()
    output_data = EsiResponse.model_validate_json(output_path.read_text())
    assert "server_version" in output_data.http_response.json_data  # type: ignore
    assert "start_time" in output_data.http_response.json_data  # type: ignore


def test_paged_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a paged EsiLink request and response handling."""
    operation_id = "GetUniverseTypes"
    output_path_str = (
        f"{test_output_dir}/test_simple_paged_request/${{OPERATION_ID}}-response.json"
    )

    response_handler = HandlerConfig(
        name="esi-link.esi_response_to_file",
        config={
            "file_path": output_path_str,
            "overwrite": False,
        },
    )

    esi_request = EsiRequest(
        request_id=uuid4(),
        operation_id=operation_id,
        handlers=[response_handler],
    )
    esi_schema_data = EsiSchema.from_schema(
        schema=esi_schema, download_date=Instant.now()
    )
    cache = InMemoryCache()
    http_client = EsiHttpRateLimited(cache=cache, esi_schema=esi_schema_data)
    handler_manager = HandlerManager()
    handler_manager.register_handler(EsiResponseToFile.name, EsiResponseToFile)
    esi_link = EsiLink(
        esi_schema=esi_schema_data,
        esi_http=http_client,
        handler_manager=handler_manager,
    )
    esi_requests = EsiRequests(
        requests_id=uuid4(),
        requests={x.request_id: x for x in [esi_request]},
    )
    asyncio.run(esi_link.execute_requests(requests=esi_requests))
    output_template = Template(output_path_str)
    output_path = Path(output_template.substitute(OPERATION_ID=operation_id))
    assert output_path.is_file()
    output_data = EsiResponse.model_validate_json(output_path.read_text())
    assert (
        len(output_data.http_response.json_data) > 1005  # type: ignore
    )  # Should be multiple pages worth of data.


def test_batched_requests(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test multiple EsiLink requests and response handling."""

    ...


def test_post_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a POST EsiLink request and response handling."""

    operation_id = "PostUniverseNames"
    output_path_str = (
        f"{test_output_dir}/test_post_request/${{OPERATION_ID}}-response.json"
    )
    response_handler = HandlerConfig(
        name="esi-link.esi_response_to_file",
        config={
            "file_path": output_path_str,
            "overwrite": True,
        },
    )
    esi_request = EsiRequest(
        request_id=uuid4(),
        operation_id=operation_id,
        handlers=[response_handler],
        request_body=[34, 35, 36],
    )
    esi_schema_data = EsiSchema.from_schema(
        schema=esi_schema, download_date=Instant.now()
    )
    cache = InMemoryCache()
    http_client = EsiHttpRateLimited(cache=cache, esi_schema=esi_schema_data)
    handler_manager = HandlerManager()
    handler_manager.register_handler(EsiResponseToFile.name, EsiResponseToFile)
    esi_link = EsiLink(
        esi_schema=esi_schema_data,
        esi_http=http_client,
        handler_manager=handler_manager,
    )
    esi_requests = EsiRequests(
        requests_id=uuid4(),
        requests={x.request_id: x for x in [esi_request]},
    )
    asyncio.run(esi_link.execute_requests(requests=esi_requests))


def test_cached_request(esi_schema: dict[str, Any], test_output_dir: Path) -> None:
    """Test a cached EsiLink request and response handling."""
    operation_id = "GetUniverseTypes"
    output_path_str = (
        f"{test_output_dir}/test_simple_cached_request/${{OPERATION_ID}}-response.json"
    )

    response_handler = HandlerConfig(
        name="esi-link.esi_response_to_file",
        config={
            "file_path": output_path_str,
            "overwrite": True,
        },
    )

    esi_request = EsiRequest(
        request_id=uuid4(),
        operation_id=operation_id,
        handlers=[response_handler],
    )
    esi_schema_data = EsiSchema.from_schema(
        schema=esi_schema, download_date=Instant.now()
    )
    cache = InMemoryCache()
    http_client = EsiHttpRateLimited(cache=cache, esi_schema=esi_schema_data)
    handler_manager = HandlerManager()
    handler_manager.register_handler(EsiResponseToFile.name, EsiResponseToFile)
    esi_link = EsiLink(
        esi_schema=esi_schema_data,
        esi_http=http_client,
        handler_manager=handler_manager,
    )
    esi_requests = EsiRequests(
        requests_id=uuid4(),
        requests={x.request_id: x for x in [esi_request]},
    )
    asyncio.run(esi_link.execute_requests(requests=esi_requests))
    asyncio.run(esi_link.execute_requests(requests=esi_requests))

    output_template = Template(output_path_str)
    output_path = Path(output_template.substitute(OPERATION_ID=operation_id))
    assert output_path.is_file()
    output_data = EsiResponse.model_validate_json(output_path.read_text())
    assert (
        len(output_data.http_response.json_data) > 1005  # type: ignore
    )  # Should be multiple pages worth of data.
    assert output_data.metrics.cache_check == "HIT"
    assert output_data.metrics.response_source == "CACHE"


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
