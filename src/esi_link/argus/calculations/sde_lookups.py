import logging
from collections.abc import Iterable
from dataclasses import dataclass

from eve_static_data.models.derived import MarketPathsDataset, NormalizedEveTypesDataset
from eve_static_data.models.pydantic.datasets import BlueprintsDataset

logger = logging.getLogger(__name__)


def manufactured_items_produced_by_blueprints(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> frozenset[int]:
    """Returns a set of item type IDs that can be produced by blueprints."""
    manufactured_items: set[int] = set()
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.manufacturing is not None:
            if blueprint.activities.manufacturing.products is not None:
                for product in blueprint.activities.manufacturing.products:
                    manufactured_items.add(product.typeID)
    return frozenset(manufactured_items)


def reaction_items_produced_by_blueprints(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> frozenset[int]:
    """Returns a set of item type IDs that can be produced by reaction blueprints."""
    reaction_items: set[int] = set()
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.reaction is not None:
            if blueprint.activities.reaction.products is not None:
                for product in blueprint.activities.reaction.products:
                    reaction_items.add(product.typeID)
    return frozenset(reaction_items)


def materials_used_in_copying(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> frozenset[int]:
    """Returns a set of item type IDs that are used as materials in copying blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.copying is not None:
            if blueprint.activities.copying.materials is not None:
                for material in blueprint.activities.copying.materials:
                    materials.add(material.typeID)
    return frozenset(materials)


def materials_used_in_invention(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> frozenset[int]:
    """Returns a set of item type IDs that are used as materials in invention blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.invention is not None:
            if blueprint.activities.invention.materials is not None:
                for material in blueprint.activities.invention.materials:
                    materials.add(material.typeID)
    return frozenset(materials)


def materials_used_in_researching_time_efficiency(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> frozenset[int]:
    """Returns a set of item type IDs that are used as materials in researching time efficiency blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.research_time is not None:
            if blueprint.activities.research_time.materials is not None:
                for material in blueprint.activities.research_time.materials:
                    materials.add(material.typeID)
    return frozenset(materials)


def materials_used_in_researching_material_efficiency(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> frozenset[int]:
    """Returns a set of item type IDs that are used as materials in researching material efficiency blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.research_material is not None:
            if blueprint.activities.research_material.materials is not None:
                for material in blueprint.activities.research_material.materials:
                    materials.add(material.typeID)
    return frozenset(materials)


def materials_used_in_reactions(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> frozenset[int]:
    """Returns a set of item type IDs that are used as materials in reaction blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.reaction is not None:
            if blueprint.activities.reaction.materials is not None:
                for material in blueprint.activities.reaction.materials:
                    materials.add(material.typeID)
    return frozenset(materials)


def materials_used_in_manufacturing(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> frozenset[int]:
    """Returns a set of item type IDs that are used as materials in manufacturing blueprints."""
    materials: set[int] = set()
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.manufacturing is not None:
            if blueprint.activities.manufacturing.materials is not None:
                for material in blueprint.activities.manufacturing.materials:
                    materials.add(material.typeID)
    return frozenset(materials)


def published_type_ids(
    normalized_eve_types: NormalizedEveTypesDataset,
) -> frozenset[int]:
    """Returns a set of item type IDs that are published."""
    published: set[int] = set()
    for type_id, type_info in normalized_eve_types.records.items():
        if type_info.published:
            published.add(type_id)
    return frozenset(published)


def market_type_ids(
    normalized_eve_types: NormalizedEveTypesDataset,
) -> frozenset[int]:
    """Returns a set of item type IDs that have a market group ID."""
    market_types: set[int] = set()
    for type_id, type_info in normalized_eve_types.records.items():
        if type_info.marketGroupID is not None:
            market_types.add(type_id)
    return frozenset(market_types)


def manufactured_items_blueprint_lookup(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> dict[int, int]:
    """Returns a mapping of item type IDs to blueprint type IDs that can produce them."""
    produced: dict[int, int] = {}
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.manufacturing is not None:
            if blueprint.activities.manufacturing.products is not None:
                for product in blueprint.activities.manufacturing.products:
                    produced[product.typeID] = blueprint.blueprintTypeID
    return produced


def reaction_items_blueprint_lookup(
    blueprints: BlueprintsDataset, published_type_ids: set[int] | None
) -> dict[int, int]:
    """Returns a mapping of item type IDs to blueprint type IDs that can produce them."""
    produced: dict[int, int] = {}
    for blueprint in blueprints.records.values():
        if (
            published_type_ids is not None
            and blueprint.blueprintTypeID not in published_type_ids
        ):
            continue
        if blueprint.activities.reaction is not None:
            if blueprint.activities.reaction.products is not None:
                for product in blueprint.activities.reaction.products:
                    produced[product.typeID] = blueprint.blueprintTypeID
    return produced


def blueprints_in_market(
    blueprints: BlueprintsDataset,
    normalized_eve_types: NormalizedEveTypesDataset,
    only_published: bool = True,
) -> frozenset[int]:
    """Returns a set of blueprint type IDs that are published and have a market group ID."""
    in_market: set[int] = set()
    for blueprint in blueprints.records.values():
        eve_type = normalized_eve_types.records.get(blueprint.blueprintTypeID)
        if eve_type is None:
            continue
        if only_published and not eve_type.published:
            continue
        if eve_type.marketGroupID is not None:
            in_market.add(blueprint.blueprintTypeID)
    return frozenset(in_market)


@dataclass
class MarketPathName:
    type_id: int
    market_path: str
    name: str


def types_market_path_name(
    type_ids: Iterable[int],
    normalized_eve_types: NormalizedEveTypesDataset,
    market_paths: MarketPathsDataset,
) -> dict[int, MarketPathName]:
    """Returns a mapping of type IDs to their market path and name.

    TODO move this to eve_static_data as a derived dataset, with all market type_ids.
    In many cases, this could be loaded instead of the full normalized EVE types dataset.
    Or, offer normalized eve types in market, and not in market datasets. Investigate
    the size differences and loading times of these datasets to determine if this would be a worthwhile optimization.

    If a type ID does not have a market group the market path will be set to "Unknown path".
    If a type ID is not found in the normalized EVE types dataset, a ValueError will be raised.
    """
    mapping: dict[int, MarketPathName] = {}
    for type_id in type_ids:
        eve_type = normalized_eve_types.records.get(type_id)
        if eve_type is None:
            msg = f"Type ID {type_id} not found in normalized EVE types dataset."
            logger.warning(msg)
            raise ValueError(msg)
        market_group_id = eve_type.marketGroupID
        market_path = (
            market_paths.records.get(market_group_id) if market_group_id else None
        )
        mapping[type_id] = MarketPathName(
            type_id=type_id,
            market_path=market_path.delimited_str_path()
            if market_path
            else "Unknown path",
            name=eve_type.name,
        )
    return mapping
