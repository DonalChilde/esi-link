"""Models for ESI Link responses.

These models represent the data returned by ESI endpoints. The model is named after the
operation_id for the endpoint. Where the response model is a container,
items in the container will be named with the suffix "Item" to distinguish them from the
container itself.

Fields may also be added to the container that have data from the query parameters or
other metadata that is not directly from the ESI response, but is relevant to the calculations.

This is a limited set of models defined for convienience in the calculations modules,
and is not intended to be a comprehensive set of models for all ESI responses. For a
more comprehensive information on the response data from the EVE Esi, see the schema docs.
"""

from dataclasses import dataclass
from typing import Literal, TypedDict


@dataclass(slots=True)
class GetMarketPricesItem:
    type_id: int
    """The item type ID of the market price."""
    adjusted_price: float | None
    """The adjusted price of the item, calculated as a volume-weighted average of recent market prices."""
    average_price: float | None
    """The average price of the item, calculated as a simple average of recent market prices."""


@dataclass(slots=True)
class GetMarketPrices:
    data: dict[int, GetMarketPricesItem]
    """A mapping of item type IDs to their corresponding market price information."""


@dataclass(slots=True)
class GetMarketsRegionIdHistoryItem:
    average: float
    date: str
    highest: float
    lowest: float
    order_count: int
    volume: float


@dataclass(slots=True)
class GetMarketsRegionIdHistory:
    region_id: int
    type_id: int
    history: dict[str, GetMarketsRegionIdHistoryItem]

    def __post_init__(self):
        """Post-initialization processing to ensure data is sorted by date."""
        # Ensure that the data dictionary is sorted by date in descending order
        self.history = dict(
            sorted(self.history.items(), key=lambda item: item[0], reverse=True)
        )

    @property
    def most_recent_date(self) -> str | None:
        """Get the most recent date from the market history data."""
        return next(iter(self.history.keys())) if self.history else None


@dataclass(slots=True)
class GetMarketsRegionIdOrdersItem:
    """Represents a market order detail."""

    duration: int
    is_buy_order: bool
    issued: str
    location_id: int
    min_volume: int
    order_id: int
    price: float
    range: str
    system_id: int
    type_id: int
    volume_remain: int
    volume_total: int


@dataclass(slots=True)
class CollectedMarketOrders:
    """Represents collected market orders for a specific region and type."""

    region_id: int
    type_id: int
    buy_orders: list[GetMarketsRegionIdOrdersItem]
    sell_orders: list[GetMarketsRegionIdOrdersItem]


@dataclass(slots=True)
class GetMarketsRegionIdOrders:
    """Represents market orders for a specific region."""

    region_id: int
    orders: dict[int, CollectedMarketOrders]


# def collect_orders_by_type(
#     region_orders: GetMarketsRegionIdOrders,
# ) -> dict[int, CollectedMarketOrders]:
#     """Collect orders by type ID and buy/sell status.

#     Args:
#         region_orders: A GetMarketsRegionIdOrders object containing market orders for a specific region.

#     Returns:
#         A dictionary mapping type IDs to CollectedMarketOrders, which contains
#         separate lists of buy and sell orders for each type ID.
#     """
#     orders_by_type: dict[int, CollectedMarketOrders] = {}
#     for type_id, orders in region_orders.orders.items():
#         if type_id not in orders_by_type:
#             orders_by_type[type_id] = CollectedMarketOrders(
#                 region_id=region_orders.region_id,
#                 type_id=type_id,
#                 buy_orders=[],
#                 sell_orders=[],
#             )
#         for order in orders:
#             if order.is_buy_order:
#                 orders_by_type[type_id].buy_orders.append(order)
#             else:
#                 orders_by_type[type_id].sell_orders.append(order)
#     return orders_by_type


class CostIndexActivity(TypedDict):
    activity: Literal[
        "manufacturing",
        "researching_time_efficiency",
        "researching_material_efficiency",
        "copying",
        "invention",
        "reaction",
    ]
    cost_index: float


@dataclass(slots=True)
class GetIndustrySystemsItem:
    solar_system_id: int
    cost_indices: list[CostIndexActivity]

    @property
    def cost_index_by_activity(self) -> dict[str, float | str]:
        """Get a mapping of activity names to their corresponding cost indices."""
        for ci in self.cost_indices:
            print(ci)
        return {ci["activity"]: ci["cost_index"] for ci in self.cost_indices}


@dataclass(slots=True)
class GetIndustrySystems:
    systems: dict[int, GetIndustrySystemsItem]
