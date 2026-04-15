"""Argus is a legendary giant from Greek mythology, known for his many eyes and his role as a watchman."""

from dataclasses import dataclass

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
