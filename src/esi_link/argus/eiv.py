"""EIVProvider implementation for calculating the Estimated Item Value (EIV) of a given type_id."""

from esi_link.argus.models.argus_models import (
    EIVProviderProtocol,
    ManufacturingBlueprint,
)
from esi_link.argus.models.esi_models import GetMarketsPrices


class EIVProvider(EIVProviderProtocol):
    def __init__(
        self,
        universe_prices: GetMarketsPrices,
        manufacturing_blueprints: dict[int, ManufacturingBlueprint],
    ):
        """Initialize the EIVProvider with the necessary data."""
        self.universe_prices = universe_prices
        self.manufacturing_blueprints = manufacturing_blueprints

    def eiv(self, type_id: int) -> float:
        """Calculate the EIV for a given type_id.

        Raises:
            ValueError: If the type_id is invalid, or if there is insufficient data to calculate the EIV.
        """
        blueprint: ManufacturingBlueprint | None = self.manufacturing_blueprints.get(
            type_id
        )
        if blueprint is None:
            raise ValueError(f"No manufacturing blueprint found for type_id {type_id}.")
        materials = blueprint.materials
        if not materials:
            raise ValueError(
                f"ManufacturingBlueprint for type_id {type_id} has no materials."
            )
        total_cost = 0.0
        for material in materials:
            market_prices = self.universe_prices.prices.get(material.type_id)
            if market_prices is None:
                raise ValueError(
                    f"No market prices found for type_id {material.type_id}."
                )
            if market_prices.adjusted_price is None:
                raise ValueError(
                    f"No adjusted price found for type_id {material.type_id}."
                )
            total_cost += market_prices.adjusted_price * material.quantity
        return total_cost
