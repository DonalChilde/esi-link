import logging

from eve_static_data.models.derived.bill_of_materials import BillsOfMaterialsDataset

from esi_link.argus.calculations.industry_base_calculations import eiv as calculate_eiv
from esi_link.argus.models.esi_models import GetMarketsPrices

logger = logging.getLogger(__name__)


def calculate_eivs(
    boms: BillsOfMaterialsDataset, prices: GetMarketsPrices
) -> dict[int, float]:
    """Calculate the EIV for each type_id in the manufacturing BOMs."""
    eivs: dict[int, float] = {}
    adjusted_prices: dict[int, float] = {
        k: v.adjusted_price
        for k, v in prices.prices.items()
        if v.adjusted_price is not None
    }
    for manufacturing_bom in boms.manufacturing_boms.values():
        try:
            eivs[manufacturing_bom.type_id] = calculate_eiv(
                manufacturing_bom.base_materials, adjusted_prices
            )
        except Exception as e:
            logger.error(
                f"Error calculating EIV for type_id {manufacturing_bom.type_id}: {e}"
            )
            eivs[
                manufacturing_bom.type_id
            ] = -1.0  # Use -1 to indicate an error in calculation
    return eivs
