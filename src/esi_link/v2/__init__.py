"""Top-level package for Esi Link."""

from pathlib import Path

import typer

__author__ = "Chad Lowe"
__email__ = "pfmsoft.dev@gmail.com"
__app_name__ = "esi-link2"
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
APPLICATION_NAME = "esi-link2"
DEFAULT_APP_DIR = Path(typer.get_app_dir(f"{NAMESPACE}-{APPLICATION_NAME}"))
USER_AGENT = f"{__app_name__}/{__version__} (+{__url__})"
