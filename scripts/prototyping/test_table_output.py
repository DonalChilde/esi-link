#!/usr/bin/env python3
"""Quick test script to see the output of operations_by_tag_table."""

from pathlib import Path

from esi_link.esi_schema.esi_api import EsiApi
from esi_link.esi_schema.schema_store import SchemaStore
from esi_link.helpers.print_operations_by_tag import operations_by_tag_table


def main():
    """Test the operations_by_tag_table function."""
    # Load the schema store from test resources
    schema_store_path = Path("tests/resources/schema/schema_store.json")
    schema_store = SchemaStore(schema_store_path)

    # Create the API instance
    api = EsiApi.from_schema_store(schema_store)

    # Generate the table
    result = operations_by_tag_table(api)

    # # Show just the first part to check formatting
    # lines = result.split("\n")
    # for line in lines[:50]:  # Show first 50 lines
    #     print(line)

    # print(f"\n... (showing first 50 lines out of {len(lines)} total lines)")
    print(result)


if __name__ == "__main__":
    main()
