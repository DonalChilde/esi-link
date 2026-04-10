"""Industry Bill of Materials (BOM) related logic."""

from dataclasses import dataclass

from eve_static_data.models.derived import NormalizedEveTypesDataset
from eve_static_data.models.pydantic.datasets import BlueprintsDataset
from eve_static_data.models.pydantic.records import Blueprints
from pydantic import BaseModel

# NOTE: because this is tied to a buildnumber and release date, this is a good data structure
# to move to eve-static-data derived datasets. Do this after we have the core logic working,
# since it will require some fiddling of the data structures to make the industry calculations work.


@dataclass(slots=True)
class PIBom:
    # Placeholder for now.
    type_id: int
    """The type ID of the item being produced."""
    portion_size: int
    """The portion size of the item being produced."""
    base_materials: dict[int, int]
    """A mapping of material type IDs to the quantity required for one run."""
    time: int
    """The time required to complete one run, in seconds."""
    skills: dict[int, int]
    """A mapping of skill type IDs to the required skill level."""


@dataclass(slots=True)
class InventionBom:
    type_id: int
    """The type ID of the blueprint item being invented."""
    produced_from: int
    """The type ID of the blueprint being used to invent the new blueprint."""
    manufactured_type_id: int
    """The type ID of the item being produced by manufacturing the invented blueprint. 
    This included to make calculating the EIV easier. -1 if the invented blueprint cannot be manufactured."""
    probability: float
    """The probability of successfully inventing the item."""
    base_runs: int
    """The number of runs that can be produced from one invention."""
    base_me: int
    """The base material efficiency level of the invention."""
    base_te: int
    """The base time efficiency level of the invention."""
    base_materials: dict[int, int]
    """A mapping of material type IDs to the quantity required for one run."""
    base_time: int
    """The time required to complete one run, in seconds."""
    skills: dict[int, int]
    """A mapping of skill type IDs to the required skill level."""


@dataclass(slots=True)
class ReactionBom:
    type_id: int
    """The type ID of the item being produced."""
    produced_from: int
    """The type ID of the blueprint being used to produce the item."""
    portion_size: int
    """The portion size of the item being produced."""
    base_materials: dict[int, int]
    """A mapping of material type IDs to the quantity required for one run."""
    base_time: int
    """The time required to complete one run, in seconds."""
    skills: dict[int, int]
    """A mapping of skill type IDs to the required skill level."""


@dataclass(slots=True)
class ManufacturingBom:
    type_id: int
    """The type ID of the item being manufactured."""
    produced_from: int
    """The type ID of the blueprint being used to manufacture the item."""
    portion_size: int
    """The portion size of the item being manufactured."""
    base_materials: dict[int, int]
    """A mapping of material type IDs to the quantity required for one run."""
    base_time: int
    """The time required to manufacture one run, in seconds."""
    skills: dict[int, int]
    """A mapping of skill type IDs to the required skill level."""


class BillsOfMaterials(BaseModel):
    """A collection of bills of materials for industry activities.

    Indexed by the type ID of the item being produced.
    """

    build_number: int
    """The build number of the ESI data used to generate the BOMs."""
    release_date: str
    """The release date of the ESI data used to generate the BOMs."""
    invention_boms: dict[int, InventionBom]
    manufacturing_boms: dict[int, ManufacturingBom]
    reaction_boms: dict[int, ReactionBom]
    pi_boms: dict[int, PIBom]


def _determine_base_runs(type_id: int) -> int:
    """Determines the base runs for a blueprint based on its type ID."""
    # FIXME: This is a placeholder implementation. The actual logic for determining base
    # runs may be more complex and may require additional data.
    return 10


def _determine_base_me(type_id: int) -> int:
    """Determines the base material efficiency for a blueprint based on its type ID."""
    # FIXME: This is a placeholder implementation. The actual logic for determining base
    # material efficiency may be more complex and may require additional data.
    return 2


def _determine_base_te(type_id: int) -> int:
    """Determines the base time efficiency for a blueprint based on its type ID."""
    # FIXME: This is a placeholder implementation. The actual logic for determining base
    # time efficiency may be more complex and may require additional data.
    return 4


def _manufacturing_result_type_id(blueprint_type_id: int, blueprint: Blueprints) -> int:
    """Determines the type ID of the item produced by manufacturing the given blueprint.

    Assumes that the blueprint has a manufacturing activity and that the manufacturing
    activity has exactly one product. If these assumptions are not met, a ValueError is raised.
    """
    if blueprint.activities.manufacturing is not None:
        manufacturing_activity = blueprint.activities.manufacturing
        if manufacturing_activity.products is None:
            raise ValueError(
                f"Manufacturing activity for blueprint type ID {blueprint_type_id} has no products."
            )
        if len(manufacturing_activity.products) > 1:
            raise ValueError(
                f"Manufacturing activity for blueprint type ID {blueprint_type_id} has multiple products."
            )
        for product in manufacturing_activity.products:
            return product.typeID
    raise ValueError(
        f"No manufacturing product found for blueprint type ID {blueprint_type_id}."
    )


def get_invention_bom(type_id: int, blueprint: Blueprints) -> InventionBom:
    """Returns the InventionBom for the given blueprint type ID.

    This function assumes that the blueprint has an invention activity and that one of
    the products of the invention activity has a type ID matching the given type ID.
    If these assumptions are not met, a ValueError is raised.
    """
    invention_bom: InventionBom | None = None
    if blueprint.activities.invention is not None:
        invention_activity = blueprint.activities.invention
        if invention_activity.products is None:
            raise ValueError(
                f"Invention activity for blueprint type ID {blueprint.blueprintTypeID} has no products."
            )
        for product in invention_activity.products:
            if product.typeID != type_id:
                continue

            base_runs = _determine_base_runs(product.typeID)
            base_me = _determine_base_me(product.typeID)
            base_te = _determine_base_te(product.typeID)
            materials = (
                invention_activity.materials
                if invention_activity.materials is not None
                else []
            )
            skills = (
                invention_activity.skills
                if invention_activity.skills is not None
                else []
            )
            invention_bom = InventionBom(
                type_id=product.typeID,
                produced_from=blueprint.blueprintTypeID,
                manufactured_type_id=_manufacturing_result_type_id(
                    blueprint_type_id=blueprint.blueprintTypeID,
                    blueprint=blueprint,
                ),
                probability=product.probability
                if product.probability is not None
                else 1.0,
                base_runs=base_runs,
                base_me=base_me,
                base_te=base_te,
                base_materials={
                    material.typeID: material.quantity for material in materials
                },
                base_time=invention_activity.time,
                skills={skill.typeID: skill.level for skill in skills},
            )
    if invention_bom is None:
        raise ValueError(
            f"No invention product found for blueprint type ID {blueprint.blueprintTypeID} with expected product type ID {type_id}."
        )
    return invention_bom


def get_manufacturing_bom(
    type_id: int, portion_size: int, blueprint: Blueprints
) -> ManufacturingBom:
    """Returns the ManufacturingBom for the given blueprint type ID and portion size.

    portion_size can be found in the EVE types dataset, and is required to properly
    calculate the quantity produced by one run of the blueprint.

    This function assumes that the blueprint has a manufacturing activity and that one of
    the products of the manufacturing activity has a type ID matching the given type ID.
    If these assumptions are not met, a ValueError is raised.
    """
    manufacturing_bom: ManufacturingBom | None = None
    if blueprint.activities.manufacturing is not None:
        manufacturing_activity = blueprint.activities.manufacturing
        if manufacturing_activity.products is None:
            raise ValueError(
                f"Manufacturing activity for blueprint type ID {blueprint.blueprintTypeID} has no products."
            )
        for product in manufacturing_activity.products:
            if product.typeID != type_id:
                continue
            materials = (
                manufacturing_activity.materials
                if manufacturing_activity.materials is not None
                else []
            )
            skills = (
                manufacturing_activity.skills
                if manufacturing_activity.skills is not None
                else []
            )
            manufacturing_bom = ManufacturingBom(
                type_id=product.typeID,
                produced_from=blueprint.blueprintTypeID,
                portion_size=portion_size,
                base_materials={
                    material.typeID: material.quantity for material in materials
                },
                base_time=manufacturing_activity.time,
                skills={skill.typeID: skill.level for skill in skills},
            )
    if manufacturing_bom is None:
        raise ValueError(
            f"No manufacturing product found for blueprint type ID {blueprint.blueprintTypeID} with expected product type ID {type_id}."
        )
    return manufacturing_bom


def get_reaction_bom(
    type_id: int, portion_size: int, blueprint: Blueprints
) -> ReactionBom:
    """Returns the ReactionBom for the given blueprint type ID and portion size.

    This function assumes that the blueprint has a reaction activity and that one of
    the products of the reaction activity has a type ID matching the given type ID.
    If these assumptions are not met, a ValueError is raised.
    """
    reaction_bom: ReactionBom | None = None
    if blueprint.activities.reaction is not None:
        reaction_activity = blueprint.activities.reaction
        if reaction_activity.products is None:
            raise ValueError(
                f"Reaction activity for blueprint type ID {blueprint.blueprintTypeID} has no products."
            )
        for product in reaction_activity.products:
            if product.typeID != type_id:
                continue
            materials = (
                reaction_activity.materials
                if reaction_activity.materials is not None
                else []
            )
            skills = (
                reaction_activity.skills if reaction_activity.skills is not None else []
            )
            reaction_bom = ReactionBom(
                type_id=product.typeID,
                produced_from=blueprint.blueprintTypeID,
                portion_size=portion_size,
                base_materials={
                    material.typeID: material.quantity for material in materials
                },
                base_time=reaction_activity.time,
                skills={skill.typeID: skill.level for skill in skills},
            )
    if reaction_bom is None:
        raise ValueError(
            f"No reaction product found for blueprint type ID {blueprint.blueprintTypeID} with expected product type ID {type_id}."
        )
    return reaction_bom


def get_invention_boms(
    blueprints: BlueprintsDataset,
) -> dict[int, InventionBom]:
    """Returns a mapping of invented item type IDs to their corresponding InventionBom objects."""
    invention_boms: dict[int, InventionBom] = {}
    for blueprint in blueprints.records.values():
        if blueprint.activities.invention is not None:
            for product in blueprint.activities.invention.products or []:
                invention_bom = get_invention_bom(product.typeID, blueprint)
                invention_boms[invention_bom.type_id] = invention_bom
    return invention_boms


def get_manufacturing_boms(
    blueprints: BlueprintsDataset,
    eve_types: NormalizedEveTypesDataset,
) -> dict[int, ManufacturingBom]:
    """Returns a mapping of manufactured item type IDs to their corresponding ManufacturingBom objects.

    Note: subassemblies cannot be be resolved until we have a complete set of
    - manufacturing BOMs
    - invention BOMs
    - reaction BOMs
    """
    manufacturing_boms: dict[int, ManufacturingBom] = {}
    for bp_type_id, blueprint in blueprints.records.items():
        if blueprint.activities.manufacturing is not None:
            blueprint_type_info = eve_types.records.get(bp_type_id)
            if blueprint_type_info is None:
                raise ValueError(
                    f"Type ID {bp_type_id} not found in normalized EVE types dataset."
                )
            manufacturing_activity = blueprint.activities.manufacturing
            if manufacturing_activity.products is None:
                raise ValueError(
                    f"Manufacturing activity for blueprint type ID {bp_type_id} has no products."
                )
            for product in manufacturing_activity.products:
                manufacturing_bom = get_manufacturing_bom(
                    type_id=product.typeID,
                    portion_size=blueprint_type_info.portionSize,
                    blueprint=blueprint,
                )
                manufacturing_boms[manufacturing_bom.type_id] = manufacturing_bom
    return manufacturing_boms


def get_reaction_boms(
    blueprints: BlueprintsDataset,
    eve_types: NormalizedEveTypesDataset,
) -> dict[int, ReactionBom]:
    """Returns a mapping of reaction product type IDs to their corresponding ReactionBom objects."""
    reaction_boms: dict[int, ReactionBom] = {}
    for bp_type_id, blueprint in blueprints.records.items():
        if blueprint.activities.reaction is not None:
            blueprint_type_info = eve_types.records.get(bp_type_id)
            if blueprint_type_info is None:
                raise ValueError(
                    f"Type ID {bp_type_id} not found in normalized EVE types dataset."
                )
            reaction_activity = blueprint.activities.reaction
            if reaction_activity.products is None:
                raise ValueError(
                    f"Reaction activity for blueprint type ID {bp_type_id} has no products."
                )
            for product in reaction_activity.products:
                reaction_bom = get_reaction_bom(
                    type_id=product.typeID,
                    portion_size=blueprint_type_info.portionSize,
                    blueprint=blueprint,
                )
                reaction_boms[reaction_bom.type_id] = reaction_bom
    return reaction_boms
