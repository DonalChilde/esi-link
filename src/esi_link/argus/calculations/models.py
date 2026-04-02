"""Data models for calculations."""

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(slots=True)
class OrderSummaryItem:
    """Represents a summary of market orders."""

    type_id: int
    """The type ID of the item."""
    is_buy_summary: bool
    """Whether the summary is for buy orders."""
    five_price: float
    """The price at which five percent of the available items can be transacted."""
    five_orders: int
    """The number of orders available at the five percent price."""
    five_items: int
    """The number of items available at the five percent price."""
    lowest: float
    """The lowest price."""
    highest: float
    """The highest price."""
    total_items: int
    """The total number of items available."""
    total_orders: int
    """The total number of orders."""
    avg_price: float
    """The average price of the available items."""
    filtered_items: int
    """The number of items that did not meet the threshold."""
    filtered_orders: int
    """The number of orders that did not meet the threshold."""


@dataclass(slots=True)
class OrderSummary:
    """Represents a summary of market orders for a specific region and type."""

    region_id: int
    solar_system_id: int | None
    type_id: int
    buy_summary: OrderSummaryItem
    sell_summary: OrderSummaryItem


class OrderSummaries(BaseModel):
    received_at: int
    region_id: int
    solar_system_id: int | None
    summaries: dict[int, OrderSummary]


@dataclass(slots=True)
class HistorySummaryItem:
    """Represents a summary of market history data for a specific region and type."""

    region_id: int
    type_id: int
    period: int
    start: str
    end: str
    missing: int
    highest: float
    average: float
    lowest: float
    order_count: int
    volume: float
