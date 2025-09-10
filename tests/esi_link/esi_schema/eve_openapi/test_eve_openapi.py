from typing import Any

import pytest

from esi_link.esi_schema.esi_api import EsiApi

# pyright: basic


def test_get_url(esi_schema: dict[str, Any]):
    client = EsiApi(spec=esi_schema, compatibility_date="2023-01-01")
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
        "openapi": "3.0.0",
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
        },
    }

    client = EsiApi(spec=spec, compatibility_date="2023-01-01")
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
    client = EsiApi(spec=esi_schema, compatibility_date="2023-01-01")
    # Should index all operations with operationId
    operation_ids = list(client.indexed_operations.keys())
    assert operation_ids
    # Pick a known operation from the schema
    assert "GetMarketsRegionIdHistory" in operation_ids
    op_schema = client.indexed_operation("GetMarketsRegionIdHistory")
    assert op_schema.operation_id == "GetMarketsRegionIdHistory"
    assert op_schema.method == "get"
    assert op_schema.path == "/markets/{region_id}/history"


def test_operation_method_and_path(esi_schema):
    client = EsiApi(spec=esi_schema, compatibility_date="2023-01-01")
    operation_id = "GetMarketsRegionIdHistory"
    assert client.operation_method(operation_id) == "get"
    assert client.operation_path(operation_id) == "/markets/{region_id}/history"


def test_invalid_operation_id_raises(esi_schema):
    client = EsiApi(spec=esi_schema, compatibility_date="2023-01-01")
    invalid_id = "NotARealOperationId"
    with pytest.raises(ValueError, match="Operation ID not found"):
        client.indexed_operation(invalid_id)
    with pytest.raises(ValueError, match="Operation ID not found"):
        client.operation_method(invalid_id)
    with pytest.raises(ValueError, match="Operation ID not found"):
        client.operation_path(invalid_id)

    with pytest.raises(ValueError, match="Operation ID not found"):
        client.is_cached(invalid_id)
