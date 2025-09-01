from pprint import pprint

from esi_link.esi_schema.eve_openapi import EveOpenApi
from esi_link.esi_schema.schema_store import SchemaStore


def test_request_parameters(schema_store: SchemaStore):
    eop = EveOpenApi.from_schema_store(schema_store)

    parameters = eop.request_parameters("GetMarketsRegionIdHistory")
    param_dict = {x["name"]: x for x in parameters if x["in"] == "path"}
    assert "region_id" in param_dict
    assert len(param_dict) == 1
    pprint(parameters, indent=2)


def test_response_parameters(schema_store: SchemaStore):
    eop = EveOpenApi.from_schema_store(schema_store)

    content = eop.response_content("GetMarketsRegionIdHistory")
    pprint(content, indent=2)
    assert "average" in content["application/json"]["schema"]["items"]["properties"]
