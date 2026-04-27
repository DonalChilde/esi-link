"""Check to see if the models in this file are still needed, or if they can be replaced by the models in the SDE module.

If they are still needed, add more fields to them as needed, and add more models as needed.
"""
# """These are the models used by the Argus module.

# Many of these models are duplications of models used by ESI, and the SDE, but this provides
# a layer of abstraction that allows us to change the underlying data sources without
# affecting the rest of the codebase.

# In many cases, these models are simplified version, with a subset of available fields.
# As needs expand, more fields will be added.
# """

# from dataclasses import dataclass
# from typing import Protocol
# from uuid import UUID


# @dataclass(slots=True)
# class SdeDataset:
#     sde_source: str
#     """The build number if sourced from the SDE, or `ESI` if sourced from ESI."""
#     valid_date: str
#     """The release date if sourced from the SDE, or the date of retrieval if sourced from ESI."""


# @dataclass(slots=True)
# class MetaLevel:
#     type_id: int
#     meta_level: int


# @dataclass(slots=True)
# class MetaLevels(SdeDataset):
#     records: dict[int, MetaLevel]


# @dataclass(slots=True)
# class Category:
#     category_id: int
#     name: str
#     published: bool


# @dataclass(slots=True)
# class Categories(SdeDataset):
#     records: dict[int, Category]


# @dataclass(slots=True)
# class Group:
#     group_id: int
#     name: str
#     category: Category
#     published: bool


# @dataclass(slots=True)
# class Groups(SdeDataset):
#     records: dict[int, Group]


# @dataclass(slots=True)
# class MarketGroup:
#     market_group_id: int
#     name: str
#     types: set[int]
#     parent_group_id: int | None


# @dataclass(slots=True)
# class MarketGroups(SdeDataset):
#     records: dict[int, MarketGroup]

#     def market_path(self, market_group_id: int) -> tuple[int, ...]:
#         """Return the path of market groups from the given market group up to the root."""
#         path: list[int] = []
#         current_group_id = market_group_id
#         while current_group_id is not None:
#             group = self.records[current_group_id]
#             path.append(group.market_group_id)
#             current_group_id = group.parent_group_id
#         return tuple(reversed(path))

#     def market_path_names(self, market_group_id: int) -> tuple[str, ...]:
#         """Return the path of market group names from the given market group up to the root."""
#         path_names: list[str] = []
#         current_group_id = market_group_id
#         while current_group_id is not None:
#             group = self.records[current_group_id]
#             path_names.append(group.name)
#             current_group_id = group.parent_group_id
#         return tuple(reversed(path_names))


# @dataclass(slots=True)
# class MetaGroup:
#     meta_group_id: int
#     name: str


# @dataclass(slots=True)
# class MetaGroups(SdeDataset):
#     records: dict[int, MetaGroup]


# @dataclass(slots=True)
# class EveType:
#     type_id: int
#     name: str
#     group_id: int
#     market_group_id: int | None
#     portion_size: int | None
#     published: bool
#     volume: float | None
#     basePrice: float | None
#     capacity: float | None
#     meta_group_id: int | None


# @dataclass(slots=True)
# class EveTypes(SdeDataset):
#     records: dict[int, EveType]


# @dataclass(slots=True)
# class Materials:
#     """Materials required to build an item."""

#     type_id: int
#     quantity: int


# @dataclass(slots=True)
# class ManufacturingBlueprint:
#     """A manufacturing blueprint, which can be used to produce items."""

#     blueprint_type_id: int
#     name: str
#     produces_type_id: int
#     produces_quantity: int
#     time: int
#     runs_available: int
#     """Either the number of runs available for bpc, or max_runs for bpo."""
#     is_copy: bool
#     is_invented: bool
#     materials: list[Materials]
#     """The base materials required to build the item."""
#     me: int
#     te: int
#     blueprint_object_id: int | None = None
#     """The unique id of the actual blueprint, if any."""


# @dataclass(slots=True)
# class CopyingBlueprint:
#     """A copying blueprint, which can be used to produce blueprints."""

#     blueprint_object_id: int
#     name: str
#     ...


# @dataclass(slots=True)
# class ResearchingBlueprint:
#     """A researching blueprint, which can be used to research blueprints."""

#     blueprint_object_id: int
#     name: str
#     ...


# @dataclass(slots=True)
# class InventionBlueprint:
#     """An invention blueprint, which can be used to invent blueprints."""

#     blueprint_object_id: int
#     name: str
#     ...


# class GroupProviderProtocol(Protocol):
#     def groups(self, group_ids: set[int]) -> dict[int, Group]:
#         """Return a dictionary of group_id to Group for the given group_ids."""
#         ...

#     def groups_dataset(self) -> Groups:
#         """Return the Groups dataset, which includes metadata about the dataset, as well as the actual groups."""
#         ...


# class CategoryProviderProtocol(Protocol):
#     def categories(self, category_ids: set[int]) -> dict[int, Category]:
#         """Return a dictionary of category_id to Category for the given category_ids."""
#         ...

#     def categories_dataset(self) -> Categories:
#         """Return the Categories dataset, which includes metadata about the dataset, as well as the actual categories."""
#         ...


# class MetaLevelProviderProtocol(Protocol):
#     def meta_levels(self, type_ids: set[int]) -> dict[int, MetaLevel]:
#         """Return a dictionary of type_id to MetaLevel for the given type_ids."""
#         ...

#     def meta_levels_dataset(self) -> MetaLevels:
#         """Return the MetaLevels dataset, which includes metadata about the dataset, as well as the actual meta levels."""
#         ...


# class MarketGroupProviderProtocol(Protocol):
#     def market_groups(self, market_group_ids: set[int]) -> dict[int, MarketGroup]:
#         """Return a dictionary of market_group_id to MarketGroup for the given market_group_ids."""
#         ...

#     def market_groups_dataset(self) -> MarketGroups:
#         """Return the MarketGroups dataset, which includes metadata about the dataset, as well as the actual market groups."""
#         ...


# @dataclass(slots=True)
# class RegionSimple:
#     region_id: int
#     name: str


# @dataclass(slots=True)
# class RegionSimpleDataset(SdeDataset):
#     records: dict[int, RegionSimple]


# @dataclass(slots=True)
# class SolarSystemSimple:
#     system_id: int
#     name: str
#     region_id: int
#     security_status: float


# @dataclass(slots=True)
# class SolarSystemSimpleDataset(SdeDataset):
#     records: dict[int, SolarSystemSimple]


# class EveTypeProviderProtocol(Protocol):
#     # needs localizedTypes, groups, market_groups, meta_groups,meta_levels
#     def eve_types(self, type_ids: set[int]) -> dict[int, EveType]:
#         """Return a dictionary of type_id to EveType for the given type_ids."""
#         ...

#     def eve_types_dataset(self) -> EveTypes:
#         """Return the EveTypes dataset, which includes metadata about the dataset, as well as the actual eve types."""
#         ...


# class EIVProviderProtocol(Protocol):
#     def eiv(self, type_id: int) -> float:
#         """Calculate the EIV for a given type_id.

#         Raises:
#             ValueError: If the type_id is invalid, or if there is insufficient data to calculate the EIV.
#         """
#         ...


# class ManufacturingFacilityProviderProtocol(Protocol):
#     def manufacturing_facility(self, location_id: int) -> str: ...


# class BlueprintProviderProtocol(Protocol):
#     def manufacturing_blueprints(
#         self, blueprint_type_ids: set[int] | None
#     ) -> dict[int, ManufacturingBlueprint]:
#         """Return a dictionary of blueprint_type_id to ManufacturingBlueprint for the given blueprint_type_ids. If blueprint_type_ids is None, return all blueprints."""
#         ...

#     def copying_blueprints(
#         self, blueprint_object_ids: set[int] | None
#     ) -> dict[int, CopyingBlueprint]:
#         """Return a dictionary of blueprint_object_id to CopyingBlueprint for the given blueprint_object_ids. If blueprint_object_ids is None, return all copying blueprints."""
#         ...

#     def researching_blueprints(
#         self, blueprint_object_ids: set[int] | None
#     ) -> dict[int, ResearchingBlueprint]:
#         """Return a dictionary of blueprint_object_id to ResearchingBlueprint for the given blueprint_object_ids. If blueprint_object_ids is None, return all researching blueprints."""
#         ...

#     def invention_blueprints(
#         self, blueprint_object_ids: set[int] | None
#     ) -> dict[int, InventionBlueprint]:
#         """Return a dictionary of blueprint_object_id to InventionBlueprint for the given blueprint_object_ids. If blueprint_object_ids is None, return all invention blueprints."""
#         ...

#     def manufacturing_products(self) -> set[tuple[int, int]]:
#         """Return a set of tuple[type_id, blueprint_id] that can be produced by the blueprints provided by this provider."""
#         ...


# class FacilityProtocol(Protocol):
#     # define the various bonuses that a facility can provide.
#     # This is used by the various industry protocols to calculate the cost and time of manufacturing, research, invention, etc.
#     @property
#     def profile_id(self) -> UUID: ...

#     def manufacturing_time_bonus(self, blueprint: ManufacturingBlueprint) -> float: ...
#     def manufacturing_me_bonus(self, blueprint: ManufacturingBlueprint) -> float: ...
#     def manufacturing_cost_bonus(self, blueprint: ManufacturingBlueprint) -> float: ...


# class ManufactureProtocol(Protocol):
#     # needs character skills, and facility bonuses, eivProvider,cost_indices
#     def cost(
#         self, blueprint: ManufacturingBlueprint, runs: int, system_id: int
#     ) -> float:
#         """Calculate the cost to manufacture an item using the given blueprint for the given number of runs.

#         TODO return type cost breakdown.

#         Raises:
#             ValueError: If the number of runs is invalid, or if there is insufficient data to calculate the cost.
#         """
#         ...

#     def time(self, blueprint: ManufacturingBlueprint, runs: int, system_id: int) -> int:
#         """Calculate the time to manufacture an item using the given blueprint for the given number of runs.

#         Raises:
#             ValueError: If the number of runs is invalid, or if there is insufficient data to calculate the time.
#         """
#         ...

#     def materials(
#         self, blueprint: ManufacturingBlueprint, runs: int
#     ) -> list[Materials]:
#         """Calculate the materials required to manufacture an item using the given blueprint for the given number of runs.

#         Raises:
#             ValueError: If the number of runs is invalid, or if there is insufficient data to calculate the materials.
#         """
#         ...

#     def bom(
#         self, blueprint: ManufacturingBlueprint, runs: int, system_id: int
#     ) -> dict[int, float]:
#         """Calculate the bill of materials (BOM) for an item using the given blueprint for the given number of runs.

#         In this context, bom is a collection of all the data required to manufacture an item, including the materials, time, and cost.
#         Does not include the cost per item for materials at this point. Include facility and skills profile? just an identifier?

#         Raises:
#             ValueError: If the number of runs is invalid, or if there is insufficient data to calculate the BOM.
#         """
#         ...


# class ArgusStaticDataProviderProtocol(
#     GroupProviderProtocol,
#     CategoryProviderProtocol,
#     MetaLevelProviderProtocol,
#     MarketGroupProviderProtocol,
#     BlueprintProviderProtocol,
#     EveTypeProviderProtocol,
# ):
#     """A Protocol that defines access to all the static data required by the Argus module.

#     While this data is mostly backed by the SDE, this abstraction allows us to change the
#     underlying data source without affecting the rest of the codebase.

#     Top level items needed:
#      - Blueprints
#      - Maps
#      - Categories


#     """
