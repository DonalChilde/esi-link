"""This module defines the ResponseHandlerPluginLoader class, which implements the ResponseHandlerPluginLoaderProtocol."""

import importlib.util
import logging
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from esi_link.handlers.errors import HandlerPluginError
from esi_link.handlers.response.handler_abc import ResponseHandlerABC
from esi_link.helpers.pydantic.serialize_as_yaml import load_from_yaml
from esi_link.models_and_protocols import (
    HandlerPluginConfigs,
    HandlerPluginLoaderConfig,
    ResponseHandlerManagerProtocol,
    ResponseHandlerPluginLoaderProtocol,
)

logger = logging.getLogger(__name__)


class ResponseHandlerPluginLoader(ResponseHandlerPluginLoaderProtocol):
    def __init__(self, config_path: Path):
        """Initialize the ResponseHandlerPluginLoader with the given configuration path."""
        self._config_path = config_path

    def __call__(self, handler_manager: ResponseHandlerManagerProtocol) -> None:
        """Apply the plugin to the given ResponseHandlerManagerProtocol instance.

        This method should register any response group handlers provided by the plugin with the
        handler manager.

        Because paths are loaded as strings, Paths are resolved to absolute paths before
        being used. This ensures that the plugin can be loaded correctly regardless of
        the current working directory.

        Args:
            handler_manager: The ResponseHandlerManagerProtocol instance to apply the plugin to.
        """
        try:
            for plugin_cls in self._load_from_config(self._config_path):
                handler_manager.register_handler(plugin_cls)
        except HandlerPluginError as e:
            logger.error(f"Failed to apply plugin: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error applying plugin: {e}")
            raise HandlerPluginError(
                f"Unexpected error applying plugin: {e}",
                {"config_path": str(self._config_path)},
            ) from e

    def _load_from_config(
        self, config_path: Path
    ) -> Iterable[type[ResponseHandlerABC]]:
        resolved_path = config_path.resolve()
        plugin_configs = load_from_yaml(resolved_path, HandlerPluginConfigs)

        for entry in plugin_configs.plugins:
            if not entry.enabled:
                logger.info(f"Entry skipped: {entry!r}")
                continue
            try:
                plugin = self._load_plugin(entry)
                yield plugin

            except HandlerPluginError as e:
                raise HandlerPluginError(
                    f"Error loading plugin: {e}", asdict(entry)
                ) from e
            except Exception as e:
                raise HandlerPluginError(
                    f"Unexpected error loading plugin: {e}", asdict(entry)
                ) from e

    def _load_plugin(
        self, plugin_config: HandlerPluginLoaderConfig
    ) -> type[ResponseHandlerABC]:
        """Load a plugin class from the given path and class name."""
        spec = importlib.util.spec_from_file_location(
            "plugin_module", plugin_config.file_path.resolve()
        )
        if spec is None or spec.loader is None:
            raise HandlerPluginError(f"Could not load plugin.", asdict(plugin_config))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, plugin_config.class_name)
        # Ensure the loaded class is a subclass of ResponseHandlerABC
        if not issubclass(cls, ResponseHandlerABC):
            raise TypeError(
                f"{plugin_config.class_name} must subclass ResponseHandlerABC"
            )
        return cls
