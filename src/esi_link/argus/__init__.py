"""Argus is a legendary giant from Greek mythology, known for his many eyes and his role as a watchman."""

from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import typer

__author__ = "Chad Lowe"
__email__ = "pfmsoft.dev@gmail.com"
__app_name__ = "argus"
__license__ = "MIT"
__url__ = "https://github.com/DonalChilde/esi-link"  # FIXME update when Argus is split from ESI Link and has its own repo

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
APP_NAMESPACE = "pfmsoft"
APPLICATION_NAME = "argus"
DEFAULT_APP_DIR = Path(typer.get_app_dir(f"{APP_NAMESPACE}-{APPLICATION_NAME}"))
USER_AGENT = f"{__app_name__}/{__version__} (+{__url__})"
ARGUS_NAMESPACE = uuid5(NAMESPACE_URL, "argus")


# FIXME refactor:
# - set up Package fields here, for eventual split of Argus from ESI Link, and eventual split of ESI Auth from ESI Link
# - move constants to this module, for eventual split of Argus from ESI Link, and eventual split of ESI Auth from ESI Link


@dataclass
class TradeHubSystem:
    region_id: int
    region_name: str
    system_id: int
    system_name: str


@dataclass
class TradeHubStation:
    hub_system: TradeHubSystem
    station_id: int
    station_name: str


TRADE_HUBS = [
    TradeHubSystem(
        region_id=10000002,
        region_name="The Forge",
        system_id=30000142,
        system_name="Jita",
    ),
    TradeHubSystem(
        region_id=10000043,
        region_name="Domain",
        system_id=30002187,
        system_name="Amarr",
    ),
    TradeHubSystem(
        region_id=10000032,
        region_name="Sinq Laison",
        system_id=30002659,
        system_name="Dodixie",
    ),
    TradeHubSystem(
        region_id=10000030,
        region_name="Heimatar",
        system_id=30002510,
        system_name="Rens",
    ),
    TradeHubSystem(
        region_id=10000042,
        region_name="Metropolis",
        system_id=30002053,
        system_name="Hek",
    ),
]
