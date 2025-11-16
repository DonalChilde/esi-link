"""Pytest configuration and fixtures for testing."""

import json
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

from tests.resources import RESOURCES_ANCHOR


# ---------------------------------------------------------------------------------
# Add an option to mark slow tests, so that they don't run every time.
# ---------------------------------------------------------------------------------
def pytest_addoption(parser: pytest.Parser) -> None:
    """Add a command line option to run slow tests."""
    # https://docs.pytest.org/en/stable/example/simple.html#control-skipping-of-tests-according-to-command-line-option
    # conftest.py must be in the root test package.
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config: pytest.Config):
    """Register the slow marker."""
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip slow tests unless --runslow is given."""
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


# ---------------------------------------------------------------------------------


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
