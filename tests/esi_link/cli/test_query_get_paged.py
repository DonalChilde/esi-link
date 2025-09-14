from pathlib import Path

import pytest
from typer.testing import CliRunner

from esi_link.cli.main_typer import app

# TODO setup fixtures to support a sepatate test environment for cli, with a test cache and schema store


@pytest.mark.slow
def test_query_get_paged(test_output_dir: Path):
    runner = CliRunner()
    json_data_path = test_output_dir / "cli" / "test_query_get_paged.json"
    json_query_path = test_output_dir / "cli" / "test_query_get_paged_query.json"
    cli_command = [
        "query",
        "get",
        "GetMarketsRegionIdOrders",
        "-p",
        "region_id=10000002",
        "-p",
        "order_type=all",
        "--no-console",
        "--json-data",
        f"{json_data_path}",
        "--json-query",
        f"{json_query_path}",
    ]
    result = runner.invoke(app, cli_command)
    assert result.exit_code == 0, result.output
    assert (
        "Getting ESI data for operation ID: GetMarketsRegionIdOrders" in result.output
    )
    assert "Completed in" in result.output
    # Check that the output file was created and has content
    with open(json_data_path, "r") as f:
        content = f.read()
        assert content.startswith("[")
        assert content.endswith("]")
        assert len(content) > 2  # Ensure there's more than just []
    # Check that the query file was created and has content
    with open(json_query_path, "r") as f:
        content = f.read()
        assert "GetMarketsRegionIdOrders" in content
        assert content.startswith("{")
        assert content.endswith("}")
        assert len(content) > 20  # Ensure there's more than just {}
