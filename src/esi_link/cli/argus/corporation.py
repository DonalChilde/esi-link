"""Commands for working with Esi corporation data."""

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from eve_static_data import SDELoader
from rich.console import Console
from whenever import Instant

from esi_link.argus import requests as argus_requests
from esi_link.argus.reports.blueprints import (
    missing_blueprints,
    owned_blueprints_report_corporation,
)
from esi_link.argus.reports.corporation_jobs import (
    generate_corporation_jobs_report,
    resolve_corporation_jobs,
)
from esi_link.cli.argus.helpers import get_argus_settings_from_context
from esi_link.cli.helpers import get_executor_from_settings_and_schema
from esi_link.helpers.dict_writer import write_dicts_to_csv
from esi_link.helpers.file_safe_string import file_safe_string
from esi_link.helpers.save_text_file import save_text_file
from esi_link.type_defs import LangEnum

app = typer.Typer(
    no_args_is_help=True, help="Commands for working with Esi corporation data."
)


@app.command()
def blueprints(
    ctx: typer.Context,
    corporation_id: Annotated[
        int, typer.Argument(help="The corporation ID to fetch blueprints for.")
    ],
    character_id: Annotated[
        int, typer.Argument(help="The character ID to use for authentication.")
    ],
    output_dir: Annotated[
        Path, typer.Argument(help="The directory to save the blueprints data to.")
    ],
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the blueprints data to the terminal. Defaults to False.",
        ),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Whether to overwrite the output file if it already exists. Defaults to False.",
        ),
    ] = False,
    lang: Annotated[
        LangEnum,
        typer.Option(
            "-l", "--lang", help="Language for the ESI response. Defaults to 'en'."
        ),
    ] = LangEnum.EN,
    sde_path: Annotated[
        Path | None,
        typer.Option(
            "--sde-path",
            help="Optional path to the EVE Static Data Export (SDE) directory. If provided, a blueprint report will be generated in addition to the raw blueprints data.",
        ),
    ] = None,
):
    """Fetch blueprints for a corporation."""
    start = perf_counter()
    argus_settings = get_argus_settings_from_context(ctx)
    esi_link_settings = argus_settings.esi_link_settings
    console = Console()
    executor = get_executor_from_settings_and_schema(settings=esi_link_settings)
    console.print(f"Fetching blueprints for corporation {corporation_id}...")
    try:
        blueprints_task = argus_requests.corporation_blueprints(
            corporation_id=corporation_id,
            character_id=character_id,
            esi_link=executor,
            lang=lang.value,
        )
        blueprints = asyncio.run(blueprints_task)
        date_str = Instant.from_timestamp_nanos(blueprints.received_at).format_iso()
        file_stem = f"corporation_{corporation_id}_blueprints_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=blueprints.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
        if sde_path:
            console.print("Generating blueprint report...")
            # TODO use the
            sde_loader = SDELoader(sde_path)
            eve_types = sde_loader.derived_datasets.normalized_eve_types()
            market_paths = sde_loader.derived_datasets.market_paths()
            report = owned_blueprints_report_corporation(
                corporation_blueprints=blueprints,
                normalized_eve_types=eve_types,
                market_paths=market_paths,
            )
            report_as_dict = {k: asdict(v) for k, v in report.items()}
            report_file_stem = (
                f"corporation_{corporation_id}_blueprints_report_{date_str}"
            )
            report_file_stem = file_safe_string(report_file_stem)
            report_save_path = save_text_file(
                text=json.dumps(report_as_dict, indent=2),
                output_dir=output_dir,
                file_name=f"{report_file_stem}.json",
                overwrite=overwrite,
            )
            write_dicts_to_csv(
                report_as_dict.values(),
                report_save_path.with_suffix(".csv"),
                overwrite,
            )
            console.print(f"Blueprints report saved to {report_save_path}")
            missing = missing_blueprints(
                owned_blueprints=set(blueprints.blueprints),
                normalized_eve_types=eve_types,
                market_paths=market_paths,
                blueprints=sde_loader.sde_datasets.blueprints(),
            )
            missing_as_dict = {k: asdict(v) for k, v in missing.items()}
            missing_file_stem = (
                f"corporation_{corporation_id}_blueprints_missing_report_{date_str}"
            )
            missing_file_stem = file_safe_string(missing_file_stem)
            missing_save_path = save_text_file(
                text=json.dumps(missing_as_dict, indent=2),
                output_dir=output_dir,
                file_name=f"{missing_file_stem}.json",
                overwrite=overwrite,
            )
            write_dicts_to_csv(
                missing_as_dict.values(),
                missing_save_path.with_suffix(".csv"),
                overwrite,
            )
            console.print(f"Missing blueprints report saved to {missing_save_path}")
    except Exception as e:
        console.print(f"[red]Error fetching corporation blueprints: {e}[/red]")
        raise typer.Exit(code=1) from e
    end = perf_counter()
    console.print(f"Blueprints data saved to {save_path} in {end - start:.2f} seconds")
    if terminal:
        console.print(blueprints.model_dump_json(indent=2))


@app.command()
def blueprint_report(
    ctx: typer.Context,
    corporation_id: Annotated[
        int,
        typer.Argument(help="The corporation ID to fetch the blueprint report for."),
    ],
    character_id: Annotated[
        int, typer.Argument(help="The character ID to use for authentication.")
    ],
    output_dir: Annotated[
        Path, typer.Argument(help="The directory to save the blueprint report to.")
    ],
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the blueprint report to the terminal. Defaults to False.",
        ),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Whether to overwrite the output file if it already exists. Defaults to False.",
        ),
    ] = False,
    lang: Annotated[
        LangEnum,
        typer.Option(
            "-l", "--lang", help="Language for the ESI response. Defaults to 'en'."
        ),
    ] = LangEnum.EN,
):
    """Fetch a blueprint report for a corporation."""
    # TODO: implement this command
    # Produce a report of the ownership status of all blueprints in the game.
    # - Requires the sde blueprints dataset,the market paths dataset, and the normalized types dataset.
    # - output includes each published blueprint, with its market path,name, the count of owned originals, owned copies, and the best me and te of each.
    # - keep the output flattened, with one line per blueprint, to make it easy to work with in tools like Excel or pandas.
    # - make this an independent function that can be called with the blueprints and datasets as arguments.
    # - can then make this a flag on the blueprints command, so that the data is fetched once and can be used for both the raw blueprints output and the report.
    #   - maybe the flag can be the sde path? if the path is provided, then the report is generated, if not, then it's not. This way we don't have to fetch the sde data if the user doesn't want the report.
    console = Console()
    console.print("[yellow]This command is not yet implemented.[/yellow]")


@app.command()
def jobs(
    ctx: typer.Context,
    corporation_id: Annotated[
        int, typer.Argument(help="The corporation ID to fetch jobs for.")
    ],
    character_id: Annotated[
        int, typer.Argument(help="The character ID to use for authentication.")
    ],
    output_dir: Annotated[
        Path, typer.Argument(help="The directory to save the jobs data to.")
    ],
    include_completed: Annotated[
        bool,
        typer.Option(
            "--include-completed",
            help="Whether to include completed jobs in the output. Defaults to False.",
        ),
    ] = False,
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the jobs data to the terminal. Defaults to False.",
        ),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Whether to overwrite the output file if it already exists. Defaults to False.",
        ),
    ] = False,
    lang: Annotated[
        LangEnum,
        typer.Option(
            "-l", "--lang", help="Language for the ESI response. Defaults to 'en'."
        ),
    ] = LangEnum.EN,
):
    """Fetch industry jobs for a corporation."""
    start = perf_counter()
    argus_settings = get_argus_settings_from_context(ctx)
    esi_link_settings = argus_settings.esi_link_settings
    console = Console()
    executor = get_executor_from_settings_and_schema(settings=esi_link_settings)
    console.print(f"Fetching industry jobs for corporation {corporation_id}...")
    try:
        jobs_task = argus_requests.corporation_jobs(
            corporation_id=corporation_id,
            character_id=character_id,
            esi_link=executor,
            include_completed=include_completed,
            lang=lang.value,
        )
        argus_jobs = asyncio.run(jobs_task)
        date_str = Instant.from_timestamp_nanos(argus_jobs.received_at).format_iso()
        file_stem = f"corporation_{corporation_id}_jobs_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=argus_jobs.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
        resolved_tasks = resolve_corporation_jobs(
            corp_jobs=argus_jobs, esi_link=executor
        )
        jobs_resolved = asyncio.run(resolved_tasks)
        resolved_file_stem = f"corporation_{corporation_id}_jobs_resolved_{date_str}"
        resolved_file_stem = file_safe_string(resolved_file_stem)
        resolved_save_path = save_text_file(
            text=jobs_resolved.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{resolved_file_stem}.json",
            overwrite=overwrite,
        )
        console.print(f"Resolved jobs data saved to {resolved_save_path}")
        report = generate_corporation_jobs_report(resolved_jobs=jobs_resolved)
        report_file_stem = f"corporation_{corporation_id}_jobs_report_{date_str}"
        report_file_stem = file_safe_string(report_file_stem)
        report_save_path = save_text_file(
            text=report,
            output_dir=output_dir,
            file_name=f"{report_file_stem}.md",
            overwrite=overwrite,
        )
        console.print(f"Jobs report saved to {report_save_path}")
    except Exception as e:
        console.print(f"[red]Error fetching corporation jobs: {e}[/red]")
        console.print_exception()
        raise typer.Exit(code=1) from e

    end = perf_counter()
    console.print(f"Jobs data saved to {save_path} in {end - start:.2f} seconds")
    if terminal:
        console.print(report)
