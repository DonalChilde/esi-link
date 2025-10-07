import json
from uuid import uuid4

from esi_link.cache.esi_memory_cache import EsiMemoryCache
from esi_link.esi_client.esi_client import EsiQuery, esi_batch_query
from esi_link.esi_client.esi_http import EsiHttp
from esi_link.esi_client.models import QueryResponse
from esi_link.esi_schema.esi_api import EsiApi
from esi_link.esi_schema.schema_store import SchemaStore


def test_single_batch_query(schema_store: SchemaStore):
    eve_api = EsiApi.from_schema_store(schema_store)
    cache = EsiMemoryCache()
    esi_http = EsiHttp(schema_api=eve_api, max_concurrent_requests=5)

    simple_query = EsiQuery(
        query_id=uuid4(),
        operation_id="GetStatus",
        path_parameters={},
        query_parameters={},
    )

    esi_batch_query((simple_query,), cache, eve_api, esi_http=esi_http)
    assert simple_query.response is not None
    json_text = json.loads(simple_query.response.text)
    print(json.dumps(json_text, indent=2))
    print(QueryResponse.model_dump_json(simple_query.response, indent=2))
    assert simple_query.response.status_code == 200
    # assert False
