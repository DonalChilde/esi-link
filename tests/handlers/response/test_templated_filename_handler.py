"""Tests for the templated filename response handler."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from whenever import Instant

from esi_link.handlers.errors import HandlerValidationError
from esi_link.handlers.response.templated_filename_handler import (
    TemplatedFilenameResponseHandler,
)
from esi_link.models_and_protocols import (
    HttpResponse,
    Request,
    RequestMetrics,
    Response,
    ResponseHandlerConfig,
    RuntimeRequestInfo,
)


def _build_response(
    *,
    include_http_response: bool = True,
    query_page: int = 1,
) -> Response:
    """Build a minimal Response model suitable for handler tests."""
    request = Request(
        operation_id="get_characters_character_id",
        path_parameters={"character_id": 90000001},
        query_parameters={"page": query_page},
        auth_character_id=90000001,
    )

    runtime_info = RuntimeRequestInfo(
        path_url="https://esi.evetech.net/latest/characters/90000001/",
        additional_query_params={"source": "test"},
        method="GET",
        is_paged=True,
        is_auth=True,
        headers={"User-Agent": "esi-link-test"},
        response_handlers=[],
        metrics=RequestMetrics(),
    )

    http_response = None
    if include_http_response:
        http_response = HttpResponse(
            status_code=200,
            url=runtime_info.path_url,
            headers={
                "Content-Type": "application/json",
                "Date": "Wed, 01 Jan 2025 00:00:00 GMT",
                "ETag": '"etag-123"',
            },
            body_text='{"ok": true}',
            received_at=Instant.now(),
        )

    return Response(
        request=request,
        runtime_info=runtime_info,
        http_response=http_response,
        exception_messages=[],
        exceptions=[],
    )


def test_validate_config_rejects_non_dict_template_values() -> None:
    """Validate that template_values must be a dictionary."""
    config = ResponseHandlerConfig(
        name=TemplatedFilenameResponseHandler.name,
        config={
            "output_dir": "./out",
            "file_name_template": "${operation_id}.json",
            "overwrite": False,
            "template_values": "not-a-dict",
        },
    )

    with pytest.raises(HandlerValidationError):
        TemplatedFilenameResponseHandler.validate_config(config)


def test_from_config_and_call_writes_nested_output(tmp_path: Path) -> None:
    """Render template metadata and write response body to a nested output path."""
    config = ResponseHandlerConfig(
        name=TemplatedFilenameResponseHandler.name,
        config={
            "output_dir": str(tmp_path),
            "file_name_template": (
                "${operation_id}/${query_page}-${status_code}-${custom_value}.json"
            ),
            "overwrite": True,
            "template_values": {"custom_value": "alpha/beta*value"},
        },
    )
    response = _build_response(query_page=7)

    TemplatedFilenameResponseHandler.validate_config(config)
    handler = TemplatedFilenameResponseHandler.from_config(config)
    asyncio.run(handler(response))

    assert handler.output_file is not None
    assert handler.output_file.exists()
    assert handler.output_file.is_relative_to(tmp_path)
    assert "get_characters_character_id" in str(handler.output_file)
    assert "7-200" in handler.output_file.name
    assert "alpha_beta_value" in handler.output_file.name
    assert handler.output_file.read_text(encoding="utf-8") == '{"ok": true}'


def test_missing_template_key_uses_safe_substitute(tmp_path: Path) -> None:
    """Keep unresolved keys non-fatal and sanitize them into a safe output name."""
    config = ResponseHandlerConfig(
        name=TemplatedFilenameResponseHandler.name,
        config={
            "output_dir": str(tmp_path),
            "file_name_template": "${operation_id}-${missing_key}.json",
            "overwrite": True,
        },
    )
    response = _build_response()

    handler = TemplatedFilenameResponseHandler.from_config(config)
    asyncio.run(handler(response))

    assert handler.output_file is not None
    assert handler.output_file.exists()
    assert "missing_key" in handler.output_file.name


def test_template_path_traversal_blocked(tmp_path: Path) -> None:
    """Reject traversal attempts that try to escape the configured output directory."""
    config = ResponseHandlerConfig(
        name=TemplatedFilenameResponseHandler.name,
        config={
            "output_dir": str(tmp_path),
            "file_name_template": "../outside.json",
            "overwrite": True,
        },
    )
    response = _build_response()

    handler = TemplatedFilenameResponseHandler.from_config(config)
    with pytest.raises(ValueError):
        asyncio.run(handler(response))


def test_filename_clipped_and_extension_preserved(tmp_path: Path) -> None:
    """Clip long filenames to max length while retaining file extension."""
    long_value = "x" * 400
    config = ResponseHandlerConfig(
        name=TemplatedFilenameResponseHandler.name,
        config={
            "output_dir": str(tmp_path),
            "file_name_template": "${operation_id}-${long_token}.json",
            "overwrite": True,
            "template_values": {"long_token": long_value},
        },
    )
    response = _build_response()

    handler = TemplatedFilenameResponseHandler.from_config(config)
    asyncio.run(handler(response))

    assert handler.output_file is not None
    assert len(handler.output_file.name) <= handler.MAX_FILENAME_LENGTH
    assert handler.output_file.suffix == ".json"


def test_call_without_http_response_uses_model_dump_fallback(tmp_path: Path) -> None:
    """Fallback to serialized Response content when no http_response is available."""
    config = ResponseHandlerConfig(
        name=TemplatedFilenameResponseHandler.name,
        config={
            "output_dir": str(tmp_path),
            "file_name_template": "${operation_id}-${status_code}.json",
            "overwrite": True,
        },
    )
    response = _build_response(include_http_response=False)

    handler = TemplatedFilenameResponseHandler.from_config(config)
    asyncio.run(handler(response))

    assert handler.output_file is not None
    assert handler.output_file.exists()
    contents = handler.output_file.read_text(encoding="utf-8")
    assert contents.startswith("{")
    assert "http_response" in contents
