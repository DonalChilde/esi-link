from esi_link.esi_schema.eve_openapi import EveOpenApi
from esi_link.esi_schema.schema_store import SchemaStore
from esi_link.helpers.format_operation_details import format_operation_details


def test_output(schema_store: SchemaStore):
    eve_api = EveOpenApi.from_schema_store(schema_store)
    operation = eve_api.operation_schema("GetMarketsRegionIdHistory")
    output = format_operation_details(operation)
    print(output)
    assert "Cache-Control" in output
    # assert False


def test_authed_endpoint(schema_store: SchemaStore):
    eve_api = EveOpenApi.from_schema_store(schema_store)
    operation = eve_api.operation_schema(
        "GetCorporationsCorporationIdContractsContractIdItems"
    )
    output = format_operation_details(operation)
    print(output)
    assert "Authorization Required" in output
    # assert False


def test_enum_in_type(schema_store: SchemaStore):
    eve_api = EveOpenApi.from_schema_store(schema_store)
    operation = eve_api.operation_schema("GetMarketsRegionIdOrders")
    output = format_operation_details(operation)
    print(output)
    assert "Possible values" in output
    assert False
