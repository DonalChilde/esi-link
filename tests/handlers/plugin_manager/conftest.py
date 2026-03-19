"""Shared fixtures for plugin loader tests."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Protocol

import pytest
from yaml import safe_dump

from esi_link.models_and_protocols import HandlerPluginLoaderConfig


class RecordingManager:
    """A simple manager test double that records registered classes."""

    def __init__(self, *, fail_with: Exception | None = None) -> None:
        """Initialize a recording manager with optional forced failure."""
        self.registered: list[type[Any]] = []
        self._fail_with = fail_with

    def register_handler(self, handler_cls: type[Any]) -> None:
        """Record a registration call or raise a configured exception."""
        if self._fail_with is not None:
            raise self._fail_with
        self.registered.append(handler_cls)


class RecordingManagerFactory(Protocol):
    """Callable protocol for creating RecordingManager instances."""

    def __call__(self, *, fail_with: Exception | None = None) -> RecordingManager:
        """Create a RecordingManager test double."""
        ...


class PluginConfigBuilder(Protocol):
    """Callable protocol for building plugin config YAML files."""

    def __call__(
        self,
        entries: list[HandlerPluginLoaderConfig],
        name: str = "plugins.yaml",
    ) -> Path:
        """Create a plugin config file and return its path."""
        ...


class ResponsePluginModuleBuilder(Protocol):
    """Callable protocol for creating response plugin module files."""

    def __call__(
        self,
        *,
        class_name: str,
        handler_name: str,
        module_name: str,
    ) -> Path:
        """Create and return a response plugin module path."""
        ...


class ResponseGroupPluginModuleBuilder(Protocol):
    """Callable protocol for creating response-group plugin module files."""

    def __call__(
        self,
        *,
        class_name: str,
        handler_name: str,
        module_name: str,
    ) -> Path:
        """Create and return a response-group plugin module path."""
        ...


@pytest.fixture
def recording_manager_factory() -> RecordingManagerFactory:
    """Provide a factory for creating recording manager test doubles."""

    def _make(*, fail_with: Exception | None = None) -> RecordingManager:
        return RecordingManager(fail_with=fail_with)

    return _make


@pytest.fixture
def make_plugin_config(tmp_path: Path) -> PluginConfigBuilder:
    """Create a plugin config YAML file and return its path."""

    def _make(
        entries: list[HandlerPluginLoaderConfig], name: str = "plugins.yaml"
    ) -> Path:
        file_path = tmp_path / name
        payload_entries: list[dict[str, Any]] = []
        for entry in entries:
            entry_dict = asdict(entry)
            entry_dict["file_path"] = str(entry_dict["file_path"])
            payload_entries.append(entry_dict)
        payload = {"plugins": payload_entries}
        file_path.write_text(safe_dump(payload), encoding="utf-8")
        return file_path

    return _make


@pytest.fixture
def make_response_plugin_module(tmp_path: Path) -> ResponsePluginModuleBuilder:
    """Create a temporary response handler plugin module."""

    def _make(*, class_name: str, handler_name: str, module_name: str) -> Path:
        module_path = tmp_path / f"{module_name}.py"
        module_path.write_text(
            (
                "from typing import Self\n"
                "from esi_link.handlers.response.handler_abc import ResponseHandlerABC\n"
                "from esi_link.models_and_protocols import Response, ResponseHandlerConfig\n\n"
                f"class {class_name}(ResponseHandlerABC):\n"
                f"    name = {handler_name!r}\n\n"
                "    def __init__(self, config: ResponseHandlerConfig) -> None:\n"
                "        self.config = config\n\n"
                "    async def __call__(self, response: Response) -> Response:\n"
                "        return response\n\n"
                "    @classmethod\n"
                "    def from_config(cls, config: ResponseHandlerConfig) -> Self:\n"
                "        return cls(config=config)\n\n"
                "    @classmethod\n"
                "    def validate_config(cls, config: ResponseHandlerConfig) -> None:\n"
                "        return None\n"
            ),
            encoding="utf-8",
        )
        return module_path

    return _make


@pytest.fixture
def make_response_group_plugin_module(
    tmp_path: Path,
) -> ResponseGroupPluginModuleBuilder:
    """Create a temporary response-group handler plugin module."""

    def _make(*, class_name: str, handler_name: str, module_name: str) -> Path:
        module_path = tmp_path / f"{module_name}.py"
        module_path.write_text(
            (
                "from typing import Self\n"
                "from esi_link.handlers.response_group.group_handler_abc import ResponseGroupHandlerABC\n"
                "from esi_link.models_and_protocols import ResponseGroup, ResponseGroupHandlerConfig\n\n"
                f"class {class_name}(ResponseGroupHandlerABC):\n"
                f"    name = {handler_name!r}\n\n"
                "    def __init__(self, config: ResponseGroupHandlerConfig) -> None:\n"
                "        self.config = config\n\n"
                "    async def __call__(self, response_group: ResponseGroup) -> ResponseGroup:\n"
                "        return response_group\n\n"
                "    @classmethod\n"
                "    def from_config(cls, config: ResponseGroupHandlerConfig) -> Self:\n"
                "        return cls(config=config)\n\n"
                "    @classmethod\n"
                "    def validate_config(cls, config: ResponseGroupHandlerConfig) -> None:\n"
                "        return None\n"
            ),
            encoding="utf-8",
        )
        return module_path

    return _make
