"""Module for industry-related calculations."""

from eve_static_data.models.pydantic.datasets import BlueprintsDataset

from esi_link.response.models import GetIndustrySystems, GetMarketPrices


class BillOfMaterials:
    """Represents the bill of materials for a given item type ID.

    Contains the required materials and their quantities needed to produce one unit of the item.
    Includes BOM for sub assemblies.
    """

    pass


def manufactured_items_produced_by_blueprints(
    blueprints: BlueprintsDataset,
) -> set[int]:
    """Returns a set of item type IDs that can be produced by blueprints."""
    manufactured_items: set[int] = set()
    for blueprint in blueprints.records.values():
        if blueprint.activities.manufacturing is not None:
            if blueprint.activities.manufacturing.products is not None:
                for product in blueprint.activities.manufacturing.products:
                    manufactured_items.add(product.typeID)
    return manufactured_items


def reaction_items_produced_by_blueprints(blueprints: BlueprintsDataset) -> set[int]:
    """Returns a set of item type IDs that can be produced by reaction blueprints."""
    reaction_items: set[int] = set()
    for blueprint in blueprints.records.values():
        if blueprint.activities.reaction is not None:
            if blueprint.activities.reaction.products is not None:
                for product in blueprint.activities.reaction.products:
                    reaction_items.add(product.typeID)
    return reaction_items


def materials_used_in_copying(
    blueprints: BlueprintsDataset,
) -> set[int]:
    """Returns a set of item type IDs that are used as materials in copying blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if blueprint.activities.copying is not None:
            if blueprint.activities.copying.materials is not None:
                for material in blueprint.activities.copying.materials:
                    materials.add(material.typeID)
    return materials


def materials_used_in_invention(
    blueprints: BlueprintsDataset,
) -> set[int]:
    """Returns a set of item type IDs that are used as materials in invention blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if blueprint.activities.invention is not None:
            if blueprint.activities.invention.materials is not None:
                for material in blueprint.activities.invention.materials:
                    materials.add(material.typeID)
    return materials


def materials_used_in_researching_time_efficiency(
    blueprints: BlueprintsDataset,
) -> set[int]:
    """Returns a set of item type IDs that are used as materials in researching time efficiency blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if blueprint.activities.research_time is not None:
            if blueprint.activities.research_time.materials is not None:
                for material in blueprint.activities.research_time.materials:
                    materials.add(material.typeID)
    return materials


def materials_used_in_researching_material_efficiency(
    blueprints: BlueprintsDataset,
) -> set[int]:
    """Returns a set of item type IDs that are used as materials in researching material efficiency blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if blueprint.activities.research_material is not None:
            if blueprint.activities.research_material.materials is not None:
                for material in blueprint.activities.research_material.materials:
                    materials.add(material.typeID)
    return materials


def materials_used_in_reactions(blueprints: BlueprintsDataset) -> set[int]:
    """Returns a set of item type IDs that are used as materials in reaction blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if blueprint.activities.reaction is not None:
            if blueprint.activities.reaction.materials is not None:
                for material in blueprint.activities.reaction.materials:
                    materials.add(material.typeID)
    return materials


def materials_used_in_manufacturing(blueprints: BlueprintsDataset) -> set[int]:
    """Returns a set of item type IDs that are used as materials in manufacturing blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if blueprint.activities.manufacturing is not None:
            if blueprint.activities.manufacturing.materials is not None:
                for material in blueprint.activities.manufacturing.materials:
                    materials.add(material.typeID)
    return materials


class IndustryCalculator:
    def __init__(
        self,
        blueprints: BlueprintsDataset,
        cost_indices: GetIndustrySystems,
        universe_pricing: GetMarketPrices,
    ):
        self.blueprints = blueprints
        self.cost_indices = cost_indices
        self.universe_pricing = universe_pricing

    def bill_of_materials(self, type_id: int) -> BillOfMaterials:
        """Calculate the bill of materials for a given item type ID.

        if the item cannot be produced from a blueprint, returns an empty dictionary.
        """
        # TODO stub
        return {}
