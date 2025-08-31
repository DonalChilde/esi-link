from typing import Any

from esi_link.esi_schema.eve_openapi import EveOpenApi


def test_get_url(esi_schema: dict[str, Any]):
    client = EveOpenApi(spec=esi_schema, compatibility_date="2023-01-01")
    op_id = "GetMarketsRegionIdHistory"
    path_params = {"region_id": 10000002}
    query_params = {"type_id": 34}
    url_with_query = client.get_url(
        op_id=op_id,
        path_params=path_params,
        query_params=query_params,
        include_query=True,
    )
    assert (
        url_with_query
        == "https://esi.evetech.net/latest/markets/10000002/history?type_id=34"
    )
    url_without_query = client.get_url(
        op_id=op_id,
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
    op_id = "GetFoo"
    path_params = {"id": 1}

    # Provide query params in reverse order to ensure sorting takes effect
    qp = {"b": 2, "a": 1}
    url_with_query = client.get_url(
        op_id=op_id,
        path_params=path_params,
        query_params=qp,
        include_query=True,
    )

    assert url_with_query == "https://esi.evetech.net/latest/foo/1?a=1&b=2"
