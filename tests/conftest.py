import json
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

from esi_link.esi_schema.schema_store import SchemaStore
from tests.resources import RESOURCES_ANCHOR


##### Add an option to mark slow tests, so that they don't run every time. #####
def pytest_addoption(parser: pytest.Parser) -> None:
    # https://docs.pytest.org/en/stable/example/simple.html#control-skipping-of-tests-according-to-command-line-option
    # conftest.py must be in the root test package.
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


#################################################################################


@pytest.fixture(scope="session", name="test_output_dir")
def test_output_dir_(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Make a temp directory for output data."""
    test_app_data_dir = tmp_path_factory.mktemp("eve-argus")
    return test_app_data_dir


@pytest.fixture(scope="session", name="esi_schema")
def esi_schema_() -> dict[str, Any]:
    """Load the ESI OpenAPI schema for testing."""
    file_resource = resources.files(RESOURCES_ANCHOR).joinpath("schema/openapi.json")
    with resources.as_file(file_resource) as schema_path:
        with open(schema_path, encoding="utf-8") as file:
            return json.load(file)


@pytest.fixture(scope="session", name="schema_store")
def schema_store_(esi_schema: dict[str, Any], test_output_dir: Path) -> SchemaStore:
    """Create a SchemaStore instance for testing."""
    file_resource = resources.files(RESOURCES_ANCHOR).joinpath(
        "schema/schema_store.json"
    )
    with resources.as_file(file_resource) as schema_path:
        dummy_store = test_output_dir / "schema-store-temp/schema-store.json"
        dummy_store.parent.mkdir(parents=True, exist_ok=True)
        dummy_store.write_text(schema_path.read_text(encoding="utf-8"))
        return SchemaStore(dummy_store)
