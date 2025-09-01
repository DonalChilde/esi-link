"""Top-level package for Esi Link."""

import logging
import logging.config
from pathlib import Path
from typing import Any

from typer import get_app_dir

__author__ = "Chad Lowe"
__email__ = "pfmsoft.dev@gmail.com"
_app_name = "Esi Link"
__description__ = "A command line first interface to the Eve Online API"

# The short X.Y.Z version.
__version__ = "0.1.0"
# The full version, including alpha/beta/rc tags.
__release__ = __version__


_config_dir = Path(get_app_dir(app_name=_app_name, force_posix=True))
CONFIG: dict[str, Any] = {
    "app_name": "Esi Link",
    "version": __version__,
    "description": "A tool for importing and exporting EVE Online data.",
    "config_dir": _config_dir,
    "default_app_path": _config_dir,
    "default_app_data_path": _config_dir / "app_data",
    "default_esi_data_path": _config_dir / "esi_data",
    "default_sde_path": Path.home() / "projects" / "eve-sde",
    "log_path": _config_dir / "logs",
    "debug_path": _config_dir / "debug",
}

CONFIG["log_path"].mkdir(parents=True, exist_ok=True)
LOG_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "consoleFormatter": {
            "format": "%(asctime)s | %(name)s | %(levelname)s : %(message)s",
        },
        "fileFormatter": {
            "format": "%(asctime)s | %(name)s | %(levelname)-8s : %(message)s",
        },
        "brief": {
            "datefmt": "%H:%M:%S",
            "format": "%(levelname)-8s; %(name)s; %(message)s;",
        },
        "single-line": {
            "datefmt": "%H:%M:%S",
            "format": "%(levelname)-8s; %(asctime)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
        },
        "multi-process": {
            "datefmt": "%H:%M:%S",
            "format": "%(levelname)-8s; [%(process)d]; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
        },
        "multi-thread": {
            "datefmt": "%H:%M:%S",
            "format": "%(levelname)-8s; %(threadName)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
        },
        "verbose": {
            "format": "%(levelname)-8s; [%(process)d]; %(threadName)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d"
            ": %(message)s"
        },
        "multiline": {
            "format": "Level: %(levelname)s\nTime: %(asctime)s\nProcess: %(process)d\nThread: %(threadName)s\nLogger"
            ": %(name)s\nPath: %(module)s:%(lineno)d\nFunction :%(funcName)s\nMessage: %(message)s\n"
        },
        "mine": {
            "format": "%(asctime)s | %(levelname)-8s | %(funcName)s | %(message)s | [in %(pathname)s | %(lineno)d]"
        },
        "mine-multi": {
            "format": "%(asctime)s | %(levelname)-8s | %(funcName)s | [in %(pathname)s | %(lineno)d]\n\t %(message)s"
        },
    },
    "handlers": {
        "file": {
            "filename": f"{CONFIG['log_path'] / 'debug.log'}",
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "formatter": "mine",
        },
        "console": {
            "level": "CRITICAL",
            "class": "logging.StreamHandler",
            "formatter": "consoleFormatter",
        },
        "rot_file_info": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "mine",
            "level": "INFO",
            "filename": f"{CONFIG['log_path'] / 'rot_info.log'}",
            "mode": "a",
            "encoding": "utf-8",
            "maxBytes": 10000000,
            "backupCount": 10,
        },
        "rot_file_warn": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "mine",
            "level": "WARNING",
            "filename": f"{CONFIG['log_path'] / 'rot_warn.log'}",
            "mode": "a",
            "encoding": "utf-8",
            "maxBytes": 500000,
            "backupCount": 4,
        },
    },
    "loggers": {
        "": {
            "handlers": ["rot_file_info", "rot_file_warn", "console"],
            "level": "DEBUG",
        },
    },
}
"""The logging config dict.

https://gist.github.com/FhyTan/bef73b8f464589cd8c740608f1e1435c

https://stackoverflow.com/questions/7507825/where-is-a-complete-example-of-logging-config-dictconfig

https://earthly.dev/blog/logging-in-python/
"""
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)
