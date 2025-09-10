import json
from uuid import UUID, uuid4

from esi_link.esi_client.esi_client import EsiQuery, esi_batch_query
from esi_link.esi_client.esi_http import EsiHttp
from esi_link.esi_client.esi_memory_cache import EsiMemoryCache
from esi_link.esi_client.models import QueryResponse
from esi_link.esi_schema.esi_api import EsiApi
from esi_link.esi_schema.schema_store import SchemaStore


def test_single_batch_query(schema_store: SchemaStore):
    eve_api = EsiApi.from_schema_store(schema_store)
    cache = EsiMemoryCache()
    esi_http = EsiHttp(schema_api=eve_api, max_concurrent_requests=5)

    queries: dict[UUID, EsiQuery] = {}
    simple_query = EsiQuery(
        query_id=uuid4(),
        operation_id="GetStatus",
        path_parameters={},
        query_parameters={},
    )
    queries[simple_query.query_id] = simple_query

    results = esi_batch_query(queries, cache, eve_api, esi_http=esi_http)
    assert len(results) == 1
    print(results)
    for query_id, response in results.items():
        json_text = json.loads(response.text)
        print(json.dumps(json_text, indent=2))
        print(QueryResponse.model_dump_json(response, indent=2))
        assert query_id in queries
        assert response.status_code == 200
    # assert False
