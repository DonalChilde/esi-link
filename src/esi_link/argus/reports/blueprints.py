from dataclasses import dataclass

from eve_static_data.models.derived import MarketPathsDataset, NormalizedEveTypesDataset
from eve_static_data.models.pydantic.datasets import BlueprintsDataset

from esi_link.argus.calculations.sde_lookups import (
    MarketPathName,
    blueprints_in_market,
    types_market_path_name,
)
from esi_link.argus.models import GetCorporationsCorporationIdBlueprints


def missing_blueprints(
    owned_blueprints: set[int],
    normalized_eve_types: NormalizedEveTypesDataset,
    market_paths: MarketPathsDataset,
    blueprints: BlueprintsDataset,
) -> dict[int, MarketPathName]:
    """Returns a mapping of missing blueprint type IDs to their market path and name."""
    in_market = blueprints_in_market(
        blueprints=blueprints,
        normalized_eve_types=normalized_eve_types,
        only_published=True,
    )
    missing = in_market - owned_blueprints
    return types_market_path_name(
        type_ids=missing,
        normalized_eve_types=normalized_eve_types,
        market_paths=market_paths,
    )


@dataclass
class BlueprintReport:
    type_id: int
    market_path: str
    name: str
    bpc: int = 0
    bpc_runs: int = 0
    bpo: int = 0
    bpc_me: int = 0
    bpc_te: int = 0
    bpo_me: int = 0
    bpo_te: int = 0


def owned_blueprints_report_corporation(
    corporation_blueprints: GetCorporationsCorporationIdBlueprints,
    normalized_eve_types: NormalizedEveTypesDataset,
    market_paths: MarketPathsDataset,
) -> dict[int, BlueprintReport]:
    """Returns a mapping of owned corporation blueprint type IDs to their market path and name."""
    # TODO add extra info to the report, such as quantity, BPC/BPO, ME/TE, etc. This will likely require changes to the data model and report structure.
    reports: dict[int, BlueprintReport] = {}
    path_names = types_market_path_name(
        type_ids=corporation_blueprints.blueprints,
        normalized_eve_types=normalized_eve_types,
        market_paths=market_paths,
    )
    for bp_type_id, bps in corporation_blueprints.blueprints.items():
        path_name = path_names.get(bp_type_id)
        if path_name is None:
            raise ValueError(f"Type ID {bp_type_id} not found in market paths dataset.")
        bpc = 0
        bpc_runs = 0
        bpo = 0
        bpc_me = 0
        bpc_te = 0
        bpo_me = 0
        bpo_te = 0
        for blueprint in bps:
            if blueprint.quantity == -2:  # BPC
                bpc_runs += blueprint.runs if blueprint.runs else 0
                bpc += blueprint.quantity
                # record the highest ME and TE for the BPC.
                bpc_me = max(bpc_me, blueprint.material_efficiency)
                bpc_te = max(bpc_te, blueprint.time_efficiency)
            elif blueprint.quantity == -1:  # BPO
                bpo += blueprint.quantity
                # record the highest ME and TE for the BPO.
                bpo_me = max(bpo_me, blueprint.material_efficiency)
                bpo_te = max(bpo_te, blueprint.time_efficiency)
            elif blueprint.quantity > 0:  # stack of unused BPOs
                bpo += blueprint.quantity
            else:
                raise ValueError(
                    f"Unexpected blueprint quantity {blueprint.quantity} for type ID {bp_type_id}."
                )
        report = BlueprintReport(
            type_id=bp_type_id,
            market_path=path_name.market_path,
            name=path_name.name,
            bpc=bpc,
            bpc_runs=bpc_runs,
            bpo=bpo,
            bpc_me=bpc_me,
            bpc_te=bpc_te,
            bpo_me=bpo_me,
            bpo_te=bpo_te,
        )
        reports[bp_type_id] = report
    return reports
