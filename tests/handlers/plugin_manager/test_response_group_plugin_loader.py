"""Tests for response-group handler plugin loader behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from esi_link.handlers.errors import HandlerPluginError
from esi_link.handlers.plugin_manager.response_group_plugin_loader import (
    ResponseGroupHandlerPluginLoader,
)
from esi_link.models_and_protocols import HandlerPluginLoaderConfig
from tests.handlers.plugin_manager.conftest import (
    PluginConfigBuilder,
    RecordingManagerFactory,
    ResponseGroupPluginModuleBuilder,
)


def test_loads_enabled_plugin_and_registers(
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    make_response_group_plugin_module: ResponseGroupPluginModuleBuilder,
) -> None:
    """Enabled response-group plugin entries should be loaded and registered."""
    plugin_file = make_response_group_plugin_module(
        class_name="GroupPluginOne",
        handler_name="my-plugin-group:one",
        module_name="group_plugin_one",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="GroupPluginOne",
                enabled=True,
            )
        ],
        name="group_plugins.yaml",
    )

    manager = recording_manager_factory()
    loader = ResponseGroupHandlerPluginLoader(config_path=config_path)
    loader(manager)

    assert len(manager.registered) == 1
    assert manager.registered[0].name == "my-plugin-group:one"


def test_skips_disabled_plugin(
    caplog: pytest.LogCaptureFixture,
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    make_response_group_plugin_module: ResponseGroupPluginModuleBuilder,
) -> None:
    """Disabled response-group entries should be skipped and logged."""
    plugin_file = make_response_group_plugin_module(
        class_name="GroupPluginDisabled",
        handler_name="my-plugin-group:disabled",
        module_name="group_plugin_disabled",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="GroupPluginDisabled",
                enabled=False,
            )
        ],
        name="group_plugins_disabled.yaml",
    )

    manager = recording_manager_factory()
    loader = ResponseGroupHandlerPluginLoader(config_path=config_path)
    loader(manager)

    assert manager.registered == []
    assert "Entry skipped" in caplog.text


def test_wraps_wrong_base_type_error(
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    tmp_path: Path,
) -> None:
    """Non-ResponseGroupHandlerABC classes should fail with wrapped context."""
    plugin_file = tmp_path / "group_not_a_handler.py"
    plugin_file.write_text(
        "class NotAGroupHandler:\n    name = 'wrong:group-type'\n",
        encoding="utf-8",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="NotAGroupHandler",
                enabled=True,
            )
        ],
        name="group_plugins_wrong_type.yaml",
    )

    manager = recording_manager_factory()
    loader = ResponseGroupHandlerPluginLoader(config_path=config_path)
    with pytest.raises(HandlerPluginError) as exc_info:
        loader(manager)

    error = exc_info.value
    assert "Unexpected error loading plugin" in str(error)
    assert error.plugin_config["class_name"] == "NotAGroupHandler"


def test_missing_config_file_raises_wrapped_error(
    recording_manager_factory: RecordingManagerFactory,
    tmp_path: Path,
) -> None:
    """Missing group plugin config files should raise top-level wrapped errors."""
    missing_config = tmp_path / "group_plugins_missing.yaml"

    manager = recording_manager_factory()
    loader = ResponseGroupHandlerPluginLoader(config_path=missing_config)
    with pytest.raises(HandlerPluginError) as exc_info:
        loader(manager)

    error = exc_info.value
    assert "Unexpected error applying plugin" in str(error)
    assert error.plugin_config["config_path"] == str(missing_config)
