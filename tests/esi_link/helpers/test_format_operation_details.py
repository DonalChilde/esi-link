from esi_link.esi_schema.esi_api import EsiApi
from esi_link.esi_schema.operation_formatters.format_operation_details import (
    format_operation_details,
)
from esi_link.esi_schema.schema_store import SchemaStore


# def test_output(schema_store: SchemaStore):
#     eve_api = EveOpenApi.from_schema_store(schema_store)
#     operation = eve_api.indexed_operation("GetMarketsRegionIdHistory")
#     output = format_operation_details(operation)
#     print(output)
#     assert "Cache-Control" in output
#     # assert False


# def test_authed_endpoint(schema_store: SchemaStore):
#     eve_api = EveOpenApi.from_schema_store(schema_store)
#     operation = eve_api.indexed_operation(
#         "GetCorporationsCorporationIdContractsContractIdItems"
#     )
#     output = format_operation_details(operation)
#     print(output)
#     assert "Authorization Required" in output
#     # assert False


# def test_enum_in_type(schema_store: SchemaStore):
#     eve_api = EveOpenApi.from_schema_store(schema_store)
#     operation = eve_api.indexed_operation("GetMarketsRegionIdOrders")
#     output = format_operation_details(operation)
#     print(output)
#     assert "Possible values" in output
#     assert False
