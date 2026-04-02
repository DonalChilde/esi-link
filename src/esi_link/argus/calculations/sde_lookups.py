from eve_static_data.models.derived import NormalizedEveTypesDataset
from eve_static_data.models.pydantic.datasets import BlueprintsDataset


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
