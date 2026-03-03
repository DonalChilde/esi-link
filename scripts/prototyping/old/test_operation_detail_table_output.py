#!/usr/bin/env python3
"""Quick test script to see the output of operations_by_tag_table."""

from pathlib import Path

from rich.console import Console

from esi_link.esi_schema.esi_api import EsiApi
from esi_link.esi_schema.operation_formatters.format_operation_details import (
    operation_detail_table,
)
from esi_link.esi_schema.schema_store import SchemaStore


def main():
    """Test the operations_by_tag_table function."""
    # Load the schema store from test resources
    schema_store_path = Path("tests/resources/schema/schema_store.json")
    schema_store = SchemaStore(schema_store_path)

    # Create the API instance
    api = EsiApi.from_schema_store(schema_store)

    indexed_operation = api.indexed_operations.get(
        "GetCharactersCharacterIdWalletTransactions"
    )
    detail_table = operation_detail_table(indexed_operation)
    console = Console()
    console.print(detail_table)


if __name__ == "__main__":
    main()
