"""This module provides an implementation of the ArgusStaticDataProviderProtocol that loads data from the EVE Static Data Export (SDE) using the eve_static_data library."""

from eve_static_data import SDELoader
from eve_static_data.models.derived.meta_level import TypesMetaLevelsDataset
from eve_static_data.models.derived.region_names import RegionNames
from eve_static_data.models.derived.system_names import SystemNames
from eve_static_data.models.pydantic import localized_datasets as LDS
from eve_static_data.models.type_defs import Lang

from esi_link.argus.models import argus_models


def categories_from_sde_dataset(
    categories_dataset: LDS.CategoriesLocalizedDataset,
) -> argus_models.Categories:
    """Convert a CategoriesLocalizedDataset from the SDE into an argus_models.Categories."""
    records: dict[int, argus_models.Category] = {}
    for record in categories_dataset.records.values():
        records[record.key] = argus_models.Category(
            category_id=record.key,
            name=record.name,
            published=record.published,
        )
    return argus_models.Categories(
        sde_source=str(categories_dataset.build_number),
        valid_date=categories_dataset.release_date,
        records=records,
    )


def groups_from_sde_dataset(
    groups_dataset: LDS.GroupsLocalizedDataset, categories: argus_models.Categories
) -> argus_models.Groups:
    """Convert a GroupsLocalizedDataset from the SDE into an argus_models.Groups."""
    records: dict[int, argus_models.Group] = {}
    for record in groups_dataset.records.values():
        records[record.key] = argus_models.Group(
            group_id=record.key,
            name=record.name,
            category=categories.records[record.categoryID],
            published=record.published,
        )
    return argus_models.Groups(
        sde_source=str(groups_dataset.build_number),
        valid_date=groups_dataset.release_date,
        records=records,
    )


def market_groups_from_sde_dataset(
    market_groups_dataset: LDS.MarketGroupsLocalizedDataset,
    market_groups_types: dict[int, set[int]],
) -> argus_models.MarketGroups:
    """Convert a MarketGroupsLocalizedDataset from the SDE into an argus_models.MarketGroups."""
    records: dict[int, argus_models.MarketGroup] = {}
    for record in market_groups_dataset.records.values():
        records[record.key] = argus_models.MarketGroup(
            market_group_id=record.key,
            name=record.name,
            # FIXME Use the derived market group types from the SDE, after implementation.
            types=market_groups_types.get(record.key, set()),
            parent_group_id=record.parentGroupID,
        )
    return argus_models.MarketGroups(
        sde_source=str(market_groups_dataset.build_number),
        valid_date=market_groups_dataset.release_date,
        records=records,
    )


def meta_groups_from_sde_dataset(
    meta_groups_dataset: LDS.MetaGroupsLocalizedDataset,
) -> argus_models.MetaGroups:
    """Convert a MetaGroupsLocalizedDataset from the SDE into an argus_models.MetaGroups."""
    records: dict[int, argus_models.MetaGroup] = {}
    for record in meta_groups_dataset.records.values():
        records[record.key] = argus_models.MetaGroup(
            meta_group_id=record.key,
            name=record.name,
        )
    return argus_models.MetaGroups(
        sde_source=str(meta_groups_dataset.build_number),
        valid_date=meta_groups_dataset.release_date,
        records=records,
    )


def meta_levels_from_sde_dataset(
    type_meta_levels_dataset: TypesMetaLevelsDataset,
) -> argus_models.MetaLevels:
    """Convert a TypesMetaLevelsDataset from the SDE into an argus_models.MetaLevels."""
    records: dict[int, argus_models.MetaLevel] = {}
    for type_id, meta_level in type_meta_levels_dataset.records.items():
        records[type_id] = argus_models.MetaLevel(
            type_id=type_id,
            meta_level=meta_level,
        )
    return argus_models.MetaLevels(
        sde_source=str(type_meta_levels_dataset.build_number),
        valid_date=type_meta_levels_dataset.release_date,
        records=records,
    )


def region_names_from_sde_dataset(
    region_names_dataset: RegionNames,
) -> argus_models.RegionSimpleDataset:
    """Convert a RegionNamesDataset from the SDE into an argus_models.RegionSimpleDataset."""
    records: dict[int, argus_models.RegionSimple] = {}
    for type_id, name in region_names_dataset.records.items():
        records[type_id] = argus_models.RegionSimple(
            region_id=type_id,
            name=name,
        )
    return argus_models.RegionSimpleDataset(
        sde_source=str(region_names_dataset.build_number),
        valid_date=region_names_dataset.release_date,
        records=records,
    )


def system_names_from_sde_dataset(
    system_names_dataset: SystemNames,
) -> argus_models.SolarSystemSimpleDataset:
    """Convert a SystemNamesDataset from the SDE into an argus_models.SolarSystemSimpleDataset."""
    records: dict[int, argus_models.SolarSystemSimple] = {}
    for type_id, record in system_names_dataset.records.items():
        records[type_id] = argus_models.SolarSystemSimple(
            system_id=type_id,
            name=record.system_name,
            region_id=record.region_id,
            security_status=record.security_status,
        )
    return argus_models.SolarSystemSimpleDataset(
        sde_source=str(system_names_dataset.build_number),
        valid_date=system_names_dataset.release_date,
        records=records,
    )


def eve_types_from_sde_dataset(
    eve_types_dataset: LDS.EveTypesLocalizedDataset,
) -> argus_models.EveTypes:
    """Convert an EveTypesLocalizedDataset from the SDE into an argus_models.EveTypes."""
    records: dict[int, argus_models.EveType] = {}

    for record in eve_types_dataset.records.values():
        records[record.key] = argus_models.EveType(
            type_id=record.key,
            name=record.name,
            group_id=record.groupID,
            market_group_id=record.marketGroupID if record.marketGroupID else None,
            meta_group_id=record.metaGroupID if record.metaGroupID else None,
            portion_size=record.portionSize,
            published=record.published,
            volume=record.volume,
            basePrice=record.basePrice,
            capacity=record.capacity,
        )
    return argus_models.EveTypes(
        sde_source=str(eve_types_dataset.build_number),
        valid_date=eve_types_dataset.release_date,
        records=records,
    )


class ArgusSdeData(argus_models.ArgusStaticDataProviderProtocol):
    def __init__(self, sde_loader: SDELoader, lang: Lang = "en"):
        """Initialize the ArgusSdeData with an SDELoader and a language for localized datasets.

        Args:
            sde_loader (SDELoader): The SDELoader to use for loading datasets from the SDE.
            lang (Lang, optional): The language to use for localized datasets. Defaults to "en".

        This implementation lazy loads datasets from the SDE, meaning that it will only
        load a dataset when it is first requested. Once a dataset is loaded, it is cached
        in memory for future use.

        The foo(set[int]) and foo_dataset() methods are separate to allow for the possibility
        of only loading a subset of the data from the SDE, if desired. For example, if
        only a few categories are needed, it may be more efficient to only load those
        categories from the SDE rather than loading the entire dataset. However, in this
        implementation, the entire dataset is loaded.

        Future implementations plan to import the SDE data into a local database, and then
        query that database for the requested data, rather than loading the entire dataset
        into memory.
        """
        self.sde_loader = sde_loader
        self.lang: Lang = lang
        self._groups: argus_models.Groups | None = None
        self._categories: argus_models.Categories | None = None
        self._market_groups: argus_models.MarketGroups | None = None
        self._meta_groups: argus_models.MetaGroups | None = None
        self._meta_levels: argus_models.MetaLevels | None = None
        self._region_names: argus_models.RegionSimpleDataset | None = None
        self._system_names: argus_models.SolarSystemSimpleDataset | None = None
        self._eve_types: argus_models.EveTypes | None = None

    def _load_categories(self) -> argus_models.Categories:
        if self._categories is None:
            categories_dataset = self.sde_loader.localized_datasets.categories(
                lang=self.lang
            )
            categories = categories_from_sde_dataset(categories_dataset)
            self._categories = categories
        return self._categories

    def _load_groups(self) -> argus_models.Groups:
        if self._groups is None:
            groups_dataset = self.sde_loader.localized_datasets.groups(lang=self.lang)
            categories = self.categories_dataset()  # This will use the cached categories if already loaded, or load them if not.
            self._groups = groups_from_sde_dataset(groups_dataset, categories)
        return self._groups

    def _load_market_groups(self) -> argus_models.MarketGroups:
        if self._market_groups is None:
            market_groups_dataset = self.sde_loader.localized_datasets.market_groups(
                lang=self.lang
            )
            # TODO implement loading of market group types from the SDE, and pass them in here.
            market_groups_types: dict[int, set[int]] = {}
            self._market_groups = market_groups_from_sde_dataset(
                market_groups_dataset, market_groups_types
            )
        return self._market_groups

    def _load_meta_groups(self) -> argus_models.MetaGroups:
        if self._meta_groups is None:
            meta_groups_dataset = self.sde_loader.localized_datasets.meta_groups(
                lang=self.lang
            )
            self._meta_groups = meta_groups_from_sde_dataset(meta_groups_dataset)
        return self._meta_groups

    def _load_meta_levels(self) -> argus_models.MetaLevels:
        if self._meta_levels is None:
            type_meta_levels_dataset = self.sde_loader.derived_datasets.meta_levels()
            self._meta_levels = meta_levels_from_sde_dataset(type_meta_levels_dataset)
        return self._meta_levels

    def _load_region_names(self) -> argus_models.RegionSimpleDataset:
        if self._region_names is None:
            region_names_dataset = self.sde_loader.derived_datasets.region_names()
            self._region_names = region_names_from_sde_dataset(region_names_dataset)
        return self._region_names

    def _load_system_names(self) -> argus_models.SolarSystemSimpleDataset:
        if self._system_names is None:
            system_names_dataset = self.sde_loader.derived_datasets.system_names()
            self._system_names = system_names_from_sde_dataset(system_names_dataset)
        return self._system_names

    def _load_eve_types(self) -> argus_models.EveTypes:
        if self._eve_types is None:
            eve_types_dataset = self.sde_loader.localized_datasets.eve_types(
                lang=self.lang
            )
            self._eve_types = eve_types_from_sde_dataset(eve_types_dataset)
        return self._eve_types

    def categories_dataset(self) -> argus_models.Categories:
        """Return the Categories dataset, which includes metadata about the dataset, as well as the actual categories."""
        return self._load_categories()

    def categories(self, category_ids: set[int]) -> dict[int, argus_models.Category]:
        """Return a dictionary of category_id to Category for the given category_ids."""
        categories_dataset = self.categories_dataset()
        return {
            category_id: categories_dataset.records[category_id]
            for category_id in category_ids
            if category_id in categories_dataset.records
        }

    def groups_dataset(self) -> argus_models.Groups:
        """Return the Groups dataset, which includes metadata about the dataset, as well as the actual groups."""
        return self._load_groups()

    def groups(self, group_ids: set[int]) -> dict[int, argus_models.Group]:
        """Return a dictionary of group_id to Group for the given group_ids."""
        groups_dataset = self.groups_dataset()
        return {
            group_id: groups_dataset.records[group_id]
            for group_id in group_ids
            if group_id in groups_dataset.records
        }

    def market_groups_dataset(self) -> argus_models.MarketGroups:
        """Return the MarketGroups dataset, which includes metadata about the dataset, as well as the actual market groups."""
        return self._load_market_groups()

    def market_groups(
        self, market_group_ids: set[int]
    ) -> dict[int, argus_models.MarketGroup]:
        """Return a dictionary of market_group_id to MarketGroup for the given market_group_ids."""
        market_groups_dataset = self.market_groups_dataset()
        return {
            market_group_id: market_groups_dataset.records[market_group_id]
            for market_group_id in market_group_ids
            if market_group_id in market_groups_dataset.records
        }

    def meta_groups_dataset(self) -> argus_models.MetaGroups:
        """Return the MetaGroups dataset, which includes metadata about the dataset, as well as the actual meta groups."""
        return self._load_meta_groups()

    def meta_groups(
        self, meta_group_ids: set[int]
    ) -> dict[int, argus_models.MetaGroup]:
        """Return a dictionary of meta_group_id to MetaGroup for the given meta_group_ids."""
        meta_groups_dataset = self.meta_groups_dataset()
        return {
            meta_group_id: meta_groups_dataset.records[meta_group_id]
            for meta_group_id in meta_group_ids
            if meta_group_id in meta_groups_dataset.records
        }

    def meta_levels_dataset(self) -> argus_models.MetaLevels:
        """Return the MetaLevels dataset, which includes metadata about the dataset, as well as the actual meta levels."""
        return self._load_meta_levels()

    def meta_levels(self, type_ids: set[int]) -> dict[int, argus_models.MetaLevel]:
        """Return a dictionary of type_id to MetaLevel for the given type_ids."""
        meta_levels_dataset = self.meta_levels_dataset()
        return {
            type_id: meta_levels_dataset.records[type_id]
            for type_id in type_ids
            if type_id in meta_levels_dataset.records
        }

    def region_names_dataset(self) -> argus_models.RegionSimpleDataset:
        """Return the RegionSimpleDataset, which includes metadata about the dataset, as well as the actual region names."""
        return self._load_region_names()

    def region_names(
        self, region_ids: set[int]
    ) -> dict[int, argus_models.RegionSimple]:
        """Return a dictionary of region_id to RegionSimple for the given region_ids."""
        region_names_dataset = self.region_names_dataset()
        return {
            region_id: region_names_dataset.records[region_id]
            for region_id in region_ids
            if region_id in region_names_dataset.records
        }

    def system_names_dataset(self) -> argus_models.SolarSystemSimpleDataset:
        """Return the SolarSystemSimpleDataset, which includes metadata about the dataset, as well as the actual system names."""
        return self._load_system_names()

    def system_names(
        self, system_ids: set[int]
    ) -> dict[int, argus_models.SolarSystemSimple]:
        """Return a dictionary of system_id to SolarSystemSimple for the given system_ids."""
        system_names_dataset = self.system_names_dataset()
        return {
            system_id: system_names_dataset.records[system_id]
            for system_id in system_ids
            if system_id in system_names_dataset.records
        }

    def eve_types_dataset(self) -> argus_models.EveTypes:
        """Return the EveTypes dataset, which includes metadata about the dataset, as well as the actual eve types."""
        return self._load_eve_types()

    def eve_types(self, type_ids: set[int]) -> dict[int, argus_models.EveType]:
        """Return a dictionary of type_id to EveType for the given type_ids."""
        eve_types_dataset = self.eve_types_dataset()
        return {
            type_id: eve_types_dataset.records[type_id]
            for type_id in type_ids
            if type_id in eve_types_dataset.records
        }
