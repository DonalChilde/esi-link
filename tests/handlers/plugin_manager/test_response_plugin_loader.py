"""Tests for response handler plugin loader behavior."""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any

import pytest

from esi_link.handlers.errors import HandlerPluginError
from esi_link.handlers.plugin_manager.response_plugin_loader import (
    ResponseHandlerPluginLoader,
)
from esi_link.models_and_protocols import HandlerPluginLoaderConfig
from tests.handlers.plugin_manager.conftest import (
    PluginConfigBuilder,
    RecordingManagerFactory,
    ResponsePluginModuleBuilder,
)


def test_loads_enabled_plugin_and_registers(
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    make_response_plugin_module: ResponsePluginModuleBuilder,
) -> None:
    """Enabled plugin entries should be loaded and registered in order."""
    plugin_file = make_response_plugin_module(
        class_name="PluginOne",
        handler_name="my-plugin:one",
        module_name="plugin_one",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="PluginOne",
                enabled=True,
            )
        ]
    )

    manager = recording_manager_factory()
    loader = ResponseHandlerPluginLoader(config_path=config_path)
    loader(manager)

    assert len(manager.registered) == 1
    assert manager.registered[0].name == "my-plugin:one"


def test_skips_disabled_plugin(
    caplog: pytest.LogCaptureFixture,
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    make_response_plugin_module: ResponsePluginModuleBuilder,
) -> None:
    """Disabled plugin entries should be skipped and logged."""
    plugin_file = make_response_plugin_module(
        class_name="PluginDisabled",
        handler_name="my-plugin:disabled",
        module_name="plugin_disabled",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="PluginDisabled",
                enabled=False,
            )
        ],
        name="plugins_disabled.yaml",
    )

    manager = recording_manager_factory()
    loader = ResponseHandlerPluginLoader(config_path=config_path)
    loader(manager)

    assert manager.registered == []
    assert "Entry skipped" in caplog.text


def test_wraps_missing_class_error(
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    make_response_plugin_module: ResponsePluginModuleBuilder,
) -> None:
    """Missing class names should raise a wrapped HandlerPluginError."""
    plugin_file = make_response_plugin_module(
        class_name="AvailableClass",
        handler_name="my-plugin:available",
        module_name="plugin_available",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="MissingClass",
                enabled=True,
            )
        ],
        name="plugins_missing_class.yaml",
    )

    manager = recording_manager_factory()
    loader = ResponseHandlerPluginLoader(config_path=config_path)
    with pytest.raises(HandlerPluginError) as exc_info:
        loader(manager)

    error = exc_info.value
    assert "Unexpected error loading plugin" in str(error)
    assert error.plugin_config["class_name"] == "MissingClass"


def test_wraps_wrong_base_type_error(
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    tmp_path: Path,
) -> None:
    """Classes that do not subclass ResponseHandlerABC should fail with context."""
    plugin_file = tmp_path / "not_a_handler.py"
    plugin_file.write_text(
        "class NotAHandler:\n    name = 'wrong:type'\n",
        encoding="utf-8",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="NotAHandler",
                enabled=True,
            )
        ],
        name="plugins_wrong_type.yaml",
    )

    manager = recording_manager_factory()
    loader = ResponseHandlerPluginLoader(config_path=config_path)
    with pytest.raises(HandlerPluginError) as exc_info:
        loader(manager)

    error = exc_info.value
    assert "Unexpected error loading plugin" in str(error)
    assert error.plugin_config["class_name"] == "NotAHandler"


def test_missing_config_file_raises_wrapped_error(
    recording_manager_factory: RecordingManagerFactory,
    tmp_path: Path,
) -> None:
    """Missing plugin config files should raise top-level wrapped plugin errors."""
    missing_config = tmp_path / "does_not_exist.yaml"

    manager = recording_manager_factory()
    loader = ResponseHandlerPluginLoader(config_path=missing_config)
    with pytest.raises(HandlerPluginError) as exc_info:
        loader(manager)

    error = exc_info.value
    assert "Unexpected error applying plugin" in str(error)
    assert error.plugin_config["config_path"] == str(missing_config)


def test_register_handler_error_is_wrapped(
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    make_response_plugin_module: ResponsePluginModuleBuilder,
) -> None:
    """Registration errors from manager should be wrapped by loader call path."""
    plugin_file = make_response_plugin_module(
        class_name="PluginRegister",
        handler_name="my-plugin:register",
        module_name="plugin_register",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="PluginRegister",
                enabled=True,
            )
        ],
        name="plugins_register_error.yaml",
    )

    manager = recording_manager_factory(fail_with=RuntimeError("register failed"))
    loader = ResponseHandlerPluginLoader(config_path=config_path)
    with pytest.raises(HandlerPluginError) as exc_info:
        loader(manager)

    error = exc_info.value
    assert "Unexpected error applying plugin" in str(error)
    assert "config_path" in error.plugin_config


def test_spec_without_loader_raises_handler_plugin_error(
    monkeypatch: pytest.MonkeyPatch,
    recording_manager_factory: RecordingManagerFactory,
    make_plugin_config: PluginConfigBuilder,
    make_response_plugin_module: ResponsePluginModuleBuilder,
) -> None:
    """If importlib provides no loader, plugin loading should fail clearly."""
    plugin_file = make_response_plugin_module(
        class_name="PluginNoLoader",
        handler_name="my-plugin:no-loader",
        module_name="plugin_no_loader",
    )
    config_path = make_plugin_config(
        [
            HandlerPluginLoaderConfig(
                file_path=plugin_file,
                class_name="PluginNoLoader",
                enabled=True,
            )
        ],
        name="plugins_no_loader.yaml",
    )

    def _fake_spec_from_file_location(
        *args: Any, **kwargs: Any
    ) -> types.SimpleNamespace:
        return types.SimpleNamespace(loader=None)

    monkeypatch.setattr(
        "esi_link.handlers.plugin_manager.response_plugin_loader.importlib.util.spec_from_file_location",
        _fake_spec_from_file_location,
    )

    manager = recording_manager_factory()
    loader = ResponseHandlerPluginLoader(config_path=config_path)
    with pytest.raises(HandlerPluginError) as exc_info:
        loader(manager)

    assert "Error loading plugin" in str(exc_info.value)
