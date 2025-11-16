"""Models for data downloaded from the EVE ESI.

esi-link is maybe a better place for these models. There is an issue about relying
on the models when the esi changes. Still, esi-link would be a logical place for them.
they are generated with datamodel-code-generator from the EVE ESI OpenAPI spec.
TODO:
- move this functionality to esi-link.
- Write a script to generate the models,
- include ruff dependency to auto fix formatting.
  - ensure type alias are used, for monos and list types.
- scope the models with the schema version, somehow.
- make releases of esi-link with the models included, differentiated by schema version.
"""

from typing import Literal, NotRequired, TypedDict


class MarketsPricesGetItem(TypedDict):
    adjusted_price: NotRequired[float]
    average_price: NotRequired[float]
    type_id: int


type MarketsPricesGet = list[MarketsPricesGetItem]


class MarketsRegionIdHistoryGetItem(TypedDict):
    average: float
    date: str
    highest: float
    lowest: float
    order_count: int
    volume: int


type MarketsRegionIdHistoryGet = list[MarketsRegionIdHistoryGetItem]


class MarketsRegionIdOrdersGetItem(TypedDict):
    duration: int
    is_buy_order: bool
    issued: str
    location_id: int
    min_volume: int
    order_id: int
    price: float
    range: Literal[
        "station",
        "region",
        "solarsystem",
        "1",
        "2",
        "3",
        "4",
        "5",
        "10",
        "20",
        "30",
        "40",
    ]
    system_id: int
    type_id: int
    volume_remain: int
    volume_total: int


type MarketsRegionIdOrdersGet = list[MarketsRegionIdOrdersGetItem]


type MarketsRegionIdTypesGet = list[int]
