"""Focused integration tests for factory plugin-loader wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from esi_link.factory import EsiLinkObjectFactory
from esi_link.handlers.response.manager import ResponseHandlerManager
from esi_link.handlers.response_group.manager import ResponseGroupHandlerManager


class _LoaderRecorder:
    """A test double that records initialization and call usage."""

    created_paths: list[Path] = []
    called_with: list[object] = []

    def __init__(self, config_path: Path) -> None:
        self.__class__.created_paths.append(config_path)

    def __call__(self, manager: object) -> None:
        self.__class__.called_with.append(manager)


class _NeverCalledLoader:
    """A loader that fails immediately if instantiated unexpectedly."""

    def __init__(self, config_path: Path) -> None:
        raise AssertionError(f"Loader should not have been created for {config_path}")


def _factory(
    *,
    response_plugins: Path | None,
    response_group_plugins: Path | None,
) -> EsiLinkObjectFactory:
    """Build a factory instance for plugin-loader wiring tests."""
    return EsiLinkObjectFactory(
        schema=object(),  # type: ignore
        cache_directory=Path("./.cache-test"),
        credentials_file=Path("./credentials-test.json"),
        tokens_dir=Path("./tokens-test"),
        response_handler_plugins_config=response_plugins,
        response_group_handler_plugins_config=response_group_plugins,
    )


def test_factory_invokes_response_plugin_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory should construct and call response plugin loader when configured."""
    _LoaderRecorder.created_paths = []
    _LoaderRecorder.called_with = []

    config_path = Path("./response-plugins.yaml")
    monkeypatch.setattr("esi_link.factory.ResponseHandlerPluginLoader", _LoaderRecorder)

    manager = _factory(
        response_plugins=config_path,
        response_group_plugins=None,
    ).response_handler_manager()

    assert isinstance(manager, ResponseHandlerManager)
    assert _LoaderRecorder.created_paths == [config_path]
    assert len(_LoaderRecorder.called_with) == 1
    assert _LoaderRecorder.called_with[0] is manager


def test_factory_invokes_response_group_plugin_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory should construct and call response-group plugin loader when configured."""
    _LoaderRecorder.created_paths = []
    _LoaderRecorder.called_with = []

    config_path = Path("./response-group-plugins.yaml")
    monkeypatch.setattr(
        "esi_link.factory.ResponseGroupHandlerPluginLoader",
        _LoaderRecorder,
    )

    manager = _factory(
        response_plugins=None,
        response_group_plugins=config_path,
    ).response_group_handler_manager()

    assert isinstance(manager, ResponseGroupHandlerManager)
    assert _LoaderRecorder.created_paths == [config_path]
    assert len(_LoaderRecorder.called_with) == 1
    assert _LoaderRecorder.called_with[0] is manager


def test_factory_without_plugin_paths_skips_loader_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory should return default managers without creating loaders when unset."""
    monkeypatch.setattr(
        "esi_link.factory.ResponseHandlerPluginLoader", _NeverCalledLoader
    )
    monkeypatch.setattr(
        "esi_link.factory.ResponseGroupHandlerPluginLoader",
        _NeverCalledLoader,
    )

    factory = _factory(response_plugins=None, response_group_plugins=None)

    response_manager = factory.response_handler_manager()
    response_group_manager = factory.response_group_handler_manager()

    assert isinstance(response_manager, ResponseHandlerManager)
    assert isinstance(response_group_manager, ResponseGroupHandlerManager)
