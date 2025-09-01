from typing import Any

import pytest

from esi_link.esi_schema.eve_openapi import EveOpenApi

# pyright: basic


def test_get_url(esi_schema: dict[str, Any]):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    path_params = {"region_id": 10000002}
    query_params = {"type_id": 34}
    url_with_query = client.build_url(
        operation_id=operation_id,
        path_params=path_params,
        query_params=query_params,
        include_query=True,
    )
    assert (
        url_with_query
        == "https://esi.evetech.net/latest/markets/10000002/history?type_id=34"
    )
    url_without_query = client.build_url(
        operation_id=operation_id,
        path_params=path_params,
        query_params=query_params,
        include_query=False,
    )
    assert (
        url_without_query == "https://esi.evetech.net/latest/markets/10000002/history"
    )


def test_get_url_sorts_query_params():
    # Minimal inline spec with two query params 'a' and 'b'
    spec: dict[str, Any] = {
        "paths": {
            "/foo/{id}": {
                "get": {
                    "operationId": "GetFoo",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
                        {
                            "name": "b",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "a",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                    ],
                }
            }
        }
    }

    client = EveOpenApi(spec=spec, compatibility_date="2023-01-01")
    operation_id = "GetFoo"
    path_params = {"id": 1}

    # Provide query params in reverse order to ensure sorting takes effect
    qp = {"b": 2, "a": 1}
    url_with_query = client.build_url(
        operation_id=operation_id,
        path_params=path_params,
        query_params=qp,
        include_query=True,
    )

    assert url_with_query == "https://esi.evetech.net/latest/foo/1?a=1&b=2"


def test_index_by_op_id(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    # Should index all operations with operationId
    operation_ids = list(client.by_operation_id.keys())
    assert operation_ids
    # Pick a known operation from the schema
    assert "GetMarketsRegionIdHistory" in operation_ids
    op_schema = client.operation_schema("GetMarketsRegionIdHistory")
    assert op_schema.operation_id == "GetMarketsRegionIdHistory"
    assert op_schema.method == "get"
    assert op_schema.path == "/markets/{region_id}/history"


def test_request_parameters(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    params = client.request_parameters(operation_id)
    # Should include both path and query parameters
    names = {p["name"] for p in params}
    assert "region_id" in names
    assert "type_id" in names or any(p["in"] == "query" for p in params)


def test_response_content_and_headers(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    content = client.response_content(operation_id)
    assert isinstance(content, dict)
    headers = client.response_headers(operation_id)
    assert isinstance(headers, dict)


def test_validate_operation_happy_path(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    path_params = {"region_id": 10000002}
    query_params = {"type_id": 34}
    assert client.validate_operation(operation_id, path_params, query_params)


def test_is_cached_and_is_paged(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    # Should be cached for GET
    assert client.is_cached(operation_id) is True
    # Should be paged if X-Pages header present (simulate)
    # Patch response_headers to include X-Pages
    orig = client.response_headers
    client.response_headers = lambda operation_id: {"X-Pages": {}}
    assert client.is_paged(operation_id) is True
    client.response_headers = orig


def test_operation_method_and_path(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    assert client.operation_method(operation_id) == "get"
    assert client.operation_path(operation_id) == "/markets/{region_id}/history"


def test_invalid_operation_id_raises(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    invalid_id = "NotARealOperationId"
    with pytest.raises(ValueError, match="Operation ID not found"):
        client.operation_schema(invalid_id)
    with pytest.raises(ValueError, match="Operation ID not found"):
        client.operation_method(invalid_id)
    with pytest.raises(ValueError, match="Operation ID not found"):
        client.operation_path(invalid_id)
    with pytest.raises(ValueError, match="Operation ID not found"):
        client.validate_operation(invalid_id, {}, {})
    with pytest.raises(ValueError, match="Operation ID not found"):
        client.is_cached(invalid_id)


def test_missing_required_path_param_raises(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    # Missing region_id
    with pytest.raises(ValueError, match="Missing required path parameters"):
        client.validate_operation(operation_id, {}, {"type_id": 34})


def test_extra_path_param_raises(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    # Extra param not in spec
    with pytest.raises(ValueError, match="Unrecognized path parameters"):
        client.validate_operation(
            operation_id, {"region_id": 10000002, "extra": 1}, {"type_id": 34}
        )


def test_missing_required_query_param_raises(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    # Remove required query param if any
    params = client.request_parameters(operation_id)
    required_query = [
        p["name"] for p in params if p.get("in") == "query" and p.get("required")
    ]
    if required_query:
        missing = {"region_id": 10000002}
        with pytest.raises(ValueError, match="Missing required query parameters"):
            client.validate_operation(operation_id, missing, {})


def test_extra_query_param_raises(esi_schema):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    # Extra query param not in spec
    with pytest.raises(ValueError, match="Unrecognized query parameters"):
        client.validate_operation(
            operation_id, {"region_id": 10000002}, {"type_id": 34, "extra": 1}
        )
