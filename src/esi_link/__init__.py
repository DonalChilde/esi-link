"""Top-level package for Esi Link."""

from pathlib import Path

import typer

__author__ = "Chad Lowe"
__email__ = "pfmsoft.dev@gmail.com"
__app_name__ = "esi-link"
__version__ = "0.1.0"
__description__ = "A command line first interface to the Eve Online API"
__license__ = "MIT"
__url__ = "https://github.com/DonalChilde/esi-link"

#######################################################################################
# Update in pyproject.toml, as uv build backend does not yet support dynamic metadata #
# https://github.com/astral-sh/uv/issues/11718                                        #
#######################################################################################
__description__ = "A command line first interface to the Eve Online API"
# The short X.Y.Z version.
__version__ = "0.1.0"
# The full version, including alpha/beta/rc tags.
__release__ = __version__
#######################################################################################
NAMESPACE = "pfmsoft"
APPLICATION_NAME = "esi-link"
DEFAULT_APP_DIR = Path(typer.get_app_dir(f"{NAMESPACE}-{APPLICATION_NAME}"))
USER_AGENT = "esi-link/0.1.0"

# CONFIG = AppConfig(name=__app_name__)
# CONFIG.log_dir.mkdir(parents=True, exist_ok=True)

# LOG_CONFIG: dict[str, Any] = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "formatters": {
#         "consoleFormatter": {
#             "format": "%(asctime)s | %(name)s | %(levelname)s : %(message)s",
#         },
#         "fileFormatter": {
#             "format": "%(asctime)s | %(name)s | %(levelname)-8s : %(message)s",
#         },
#         "brief": {
#             "datefmt": "%H:%M:%S",
#             "format": "%(levelname)-8s; %(name)s; %(message)s;",
#         },
#         "single-line": {
#             "datefmt": "%H:%M:%S",
#             "format": "%(levelname)-8s; %(asctime)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
#         },
#         "multi-process": {
#             "datefmt": "%H:%M:%S",
#             "format": "%(levelname)-8s; [%(process)d]; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
#         },
#         "multi-thread": {
#             "datefmt": "%H:%M:%S",
#             "format": "%(levelname)-8s; %(threadName)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d: %(message)s",
#         },
#         "verbose": {
#             "format": "%(levelname)-8s; [%(process)d]; %(threadName)s; %(name)s; %(module)s:%(funcName)s;%(lineno)d"
#             ": %(message)s"
#         },
#         "multiline": {
#             "format": "Level: %(levelname)s\nTime: %(asctime)s\nProcess: %(process)d\nThread: %(threadName)s\nLogger"
#             ": %(name)s\nPath: %(module)s:%(lineno)d\nFunction :%(funcName)s\nMessage: %(message)s\n"
#         },
#         "mine": {
#             "format": "%(asctime)s | %(levelname)-8s | %(funcName)s | %(message)s | [in %(pathname)s | %(lineno)d]"
#         },
#         "mine-multi": {
#             "format": "%(asctime)s | %(levelname)-8s | %(funcName)s | [in %(pathname)s | %(lineno)d]\n\t %(message)s"
#         },
#     },
#     "handlers": {
#         "file": {
#             "filename": CONFIG.log_dir / "debug.log",
#             "level": "DEBUG",
#             "class": "logging.FileHandler",
#             "formatter": "mine",
#         },
#         "console": {
#             "level": "CRITICAL",
#             "class": "logging.StreamHandler",
#             "formatter": "consoleFormatter",
#         },
#         "rot_file_info": {
#             "class": "logging.handlers.RotatingFileHandler",
#             "formatter": "mine",
#             "level": "INFO",
#             "filename": CONFIG.log_dir / "rotating_info.log",
#             "mode": "a",
#             "encoding": "utf-8",
#             "maxBytes": 10000000,
#             "backupCount": 10,
#         },
#         "rot_file_warn": {
#             "class": "logging.handlers.RotatingFileHandler",
#             "formatter": "mine",
#             "level": "WARNING",
#             "filename": CONFIG.log_dir / "rotating_warn.log",
#             "mode": "a",
#             "encoding": "utf-8",
#             "maxBytes": 500000,
#             "backupCount": 4,
#         },
#     },
#     "loggers": {
#         "": {
#             "handlers": ["rot_file_info", "rot_file_warn", "console"],
#             "level": "DEBUG",
#         },
#     },
# }
# """The logging config dict.

# https://gist.github.com/FhyTan/bef73b8f464589cd8c740608f1e1435c

# https://stackoverflow.com/questions/7507825/where-is-a-complete-example-of-logging-config-dictconfig

# https://earthly.dev/blog/logging-in-python/
# """
# logging.config.dictConfig(LOG_CONFIG)
# logger = logging.getLogger(__name__)
