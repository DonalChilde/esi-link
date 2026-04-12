from esi_link.argus.models.argus_models import (
    BlueprintProviderProtocol,
    EIVProviderProtocol,
    ManufacturingBlueprint,
)
from esi_link.argus.models.esi_models import GetMarketsPrices


class EIVProvider(EIVProviderProtocol):
    def __init__(
        self,
        prices_provider: GetMarketsPrices,
        blueprint_provider: BlueprintProviderProtocol,
    ):
        self.prices_provider = prices_provider
        self.blueprint_provider = blueprint_provider

    def eiv(self, type_id: int) -> float:
        """Calculate the EIV for a given type_id.

        Raises:
            ValueError: If the type_id is invalid, or if there is insufficient data to calculate the EIV.
        """
        blueprint: ManufacturingBlueprint | None = (
            self.blueprint_provider.manufacturing_blueprint_by_produces_type_id(type_id)
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
            market_prices = self.prices_provider.prices.get(material.type_id)
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
