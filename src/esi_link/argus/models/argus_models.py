"""These are the models used by the Argus module.

Many of these models are duplications of models used by ESI, and the SDE, but this provides
a layer of abstraction that allows us to change the underlying data sources without
affecting the rest of the codebase.

In many cases, these models are simplified version, with a subset of available fields.
As needs expand, more fields will be added.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(slots=True)
class Category:
    category_id: int
    name: str
    published: bool


@dataclass(slots=True)
class Group:
    group_id: int
    name: str
    category: Category
    published: bool


@dataclass(slots=True)
class MarketGroup:
    market_group_id: int
    name: str
    types: set[int]
    parent_group_id: int | None


@dataclass(slots=True)
class MetaGroup:
    meta_group_id: int
    name: str


@dataclass(slots=True)
class EveType:
    type_id: int
    name: str
    group: Group
    market_group: MarketGroup | None
    meta_level: int | None
    portion_size: int | None
    published: bool
    volume: float | None
    basePrice: float | None
    capacity: float | None
    meta_group: MetaGroup | None


@dataclass(slots=True)
class Materials:
    """Materials required to build an item."""

    type_id: int
    quantity: int


@dataclass(slots=True)
class ManufacturingBlueprint:
    """A manufacturing blueprint, which can be used to produce items."""

    blueprint_type_id: int
    name: str
    produces_type_id: int
    produces_quantity: int
    time: int
    runs_available: int
    """Either the number of runs available for bpc, or max_runs for bpo."""
    is_copy: bool
    is_invented: bool
    materials: list[Materials]
    """The base materials required to build the item."""
    me: int
    te: int
    blueprint_object_id: int | None = None
    """The unique id of the actual blueprint, if any."""


class GroupProviderProtocol(Protocol):
    def group(self, group_id: int) -> Group: ...


class MarketGroupProviderProtocol(Protocol):
    def market_group(self, market_group_id: int) -> MarketGroup: ...


class EveTypeProviderProtocol(Protocol):
    # needs localizedTypes, groups, market_groups, meta_groups,meta_levels
    def eve_type(self, type_id: int) -> EveType: ...


class EIVProviderProtocol(Protocol):
    def eiv(self, type_id: int) -> float:
        """Calculate the EIV for a given type_id.

        Raises:
            ValueError: If the type_id is invalid, or if there is insufficient data to calculate the EIV.
        """
        ...


class ManufacturingFacilityProviderProtocol(Protocol):
    def manufacturing_facility(self, location_id: int) -> str: ...


class BlueprintProviderProtocol(Protocol):
    def manufacturing_blueprint_by_produces_type_id(
        self, produces_type_id: int
    ) -> ManufacturingBlueprint | None: ...
    def manufacturing_blueprint_by_blueprint_type_id(
        self, blueprint_type_id: int
    ) -> ManufacturingBlueprint | None: ...
    def manufacturing_blueprint_by_blueprint_object_id(
        self, blueprint_object_id: int
    ) -> ManufacturingBlueprint | None: ...
    def manufacturing_products(self) -> set[int]:
        """Return a set of type_ids that can be produced by the blueprints provided by this provider."""
        ...

    def manufacturing_blueprints(self) -> set[int]:
        """Return a set of blueprint_type_ids for the blueprints provided by this provider."""
        ...

    def manufacturing_blueprint_objects(self) -> set[int]:
        """Return a set of blueprint_object_ids for the blueprints provided by this provider."""
        ...


class FacilityProtocol(Protocol):
    # define the various bonuses that a facility can provide.
    # This is used by the various industry protocols to calculate the cost and time of manufacturing, research, invention, etc.
    @property
    def profile_id(self) -> UUID: ...

    def manufacturing_time_bonus(self, blueprint: ManufacturingBlueprint) -> float: ...
    def manufacturing_me_bonus(self, blueprint: ManufacturingBlueprint) -> float: ...
    def manufacturing_cost_bonus(self, blueprint: ManufacturingBlueprint) -> float: ...


class ManufactureProtocol(Protocol):
    # needs character skills, and facility bonuses, eivProvider,cost_indices
    def cost(
        self, blueprint: ManufacturingBlueprint, runs: int, system_id: int
    ) -> float:
        """Calculate the cost to manufacture an item using the given blueprint for the given number of runs.

        TODO return type cost breakdown.

        Raises:
            ValueError: If the number of runs is invalid, or if there is insufficient data to calculate the cost.
        """
        ...

    def time(self, blueprint: ManufacturingBlueprint, runs: int, system_id: int) -> int:
        """Calculate the time to manufacture an item using the given blueprint for the given number of runs.

        Raises:
            ValueError: If the number of runs is invalid, or if there is insufficient data to calculate the time.
        """
        ...

    def materials(
        self, blueprint: ManufacturingBlueprint, runs: int
    ) -> list[Materials]:
        """Calculate the materials required to manufacture an item using the given blueprint for the given number of runs.

        Raises:
            ValueError: If the number of runs is invalid, or if there is insufficient data to calculate the materials.
        """
        ...

    def bom(
        self, blueprint: ManufacturingBlueprint, runs: int, system_id: int
    ) -> dict[int, float]:
        """Calculate the bill of materials (BOM) for an item using the given blueprint for the given number of runs.

        In this context, bom is a collection of all the data required to manufacture an item, including the materials, time, and cost.
        Does not include the cost per item for materials at this point. Include facility and skills profile? just an identifier?

        Raises:
            ValueError: If the number of runs is invalid, or if there is insufficient data to calculate the BOM.
        """
        ...
