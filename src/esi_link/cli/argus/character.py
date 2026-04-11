"""Commands for working with Esi character data."""

import asyncio
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from rich.console import Console
from whenever import Instant

from esi_link.argus import requests as argus_requests
from esi_link.cli.argus.helpers import get_argus_settings_from_context
from esi_link.cli.helpers import get_executor_from_settings_and_schema
from esi_link.helpers.file_safe_string import file_safe_string
from esi_link.helpers.save_text_file import save_text_file
from esi_link.type_defs import LangEnum

app = typer.Typer(
    no_args_is_help=True, help="Commands for working with Esi character data."
)


@app.command()
def blueprints(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(help="The character ID to fetch blueprints for.")
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
):
    """Fetch blueprints for a character."""
    start = perf_counter()
    argus_settings = get_argus_settings_from_context(ctx)
    esi_link_settings = argus_settings.esi_link_settings
    console = Console()
    executor = get_executor_from_settings_and_schema(settings=esi_link_settings)
    console.print(f"Fetching blueprints for character {character_id}...")
    try:
        blueprints_task = argus_requests.character_blueprints(
            character_id=character_id, esi_link=executor, lang=lang.value
        )
        blueprints = asyncio.run(blueprints_task)
        date_str = Instant.from_timestamp_nanos(blueprints.received_at).format_iso()
        file_stem = f"character_{character_id}_blueprints_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=blueprints.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
    except Exception as e:
        console.print(f"[red]Error fetching character blueprints: {e}[/red]")
        raise typer.Exit(code=1) from e
    end = perf_counter()
    console.print(f"Blueprints saved to {save_path} in {end - start:.2f} seconds.")
    if terminal:
        console.print(blueprints.model_dump_json(indent=2))


@app.command()
def information(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(help="The character ID to fetch information for.")
    ],
    output_dir: Annotated[
        Path,
        typer.Argument(help="The directory to save the character information data to."),
    ],
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the character information data to the terminal. Defaults to False.",
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
    """Fetch information for a character."""
    start = perf_counter()
    argus_settings = get_argus_settings_from_context(ctx)
    esi_link_settings = argus_settings.esi_link_settings
    console = Console()
    executor = get_executor_from_settings_and_schema(settings=esi_link_settings)
    console.print(f"Fetching information for character {character_id}...")
    try:
        character_info_task = argus_requests.character_information(
            character_id=character_id, esi_link=executor, lang=lang.value
        )
        character_info = asyncio.run(character_info_task)
        date_str = Instant.from_timestamp_nanos(character_info.received_at).format_iso()
        file_stem = f"character_{character_id}_information_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=character_info.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
    except Exception as e:
        console.print(f"[red]Error fetching character information: {e}[/red]")
        raise typer.Exit(code=1) from e
    end = perf_counter()
    console.print(
        f"Character information saved to {save_path} in {end - start:.2f} seconds."
    )
    if terminal:
        console.print(character_info.model_dump_json(indent=2))


def jobs(
    ctx: typer.Context,
    character_id: Annotated[
        int, typer.Argument(help="The character ID to fetch industry jobs for.")
    ],
    output_dir: Annotated[
        Path,
        typer.Argument(
            help="The directory to save the character industry jobs data to."
        ),
    ],
    include_completed: Annotated[
        bool,
        typer.Option(
            "--include-completed",
            help="Whether to include completed industry jobs in the response. Defaults to False.",
        ),
    ] = False,
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the character industry jobs data to the terminal. Defaults to False.",
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
    """Fetch industry jobs for a character."""
    start = perf_counter()
    argus_settings = get_argus_settings_from_context(ctx)
    esi_link_settings = argus_settings.esi_link_settings
    console = Console()
    executor = get_executor_from_settings_and_schema(settings=esi_link_settings)
    console.print(f"Fetching industry jobs for character {character_id}...")
    try:
        jobs_task = argus_requests.character_jobs(
            character_id=character_id,
            esi_link=executor,
            include_completed=include_completed,
            lang=lang.value,
        )
        jobs = asyncio.run(jobs_task)
        date_str = Instant.from_timestamp_nanos(jobs.received_at).format_iso()
        file_stem = f"character_{character_id}_industry_jobs_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=jobs.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
    except Exception as e:
        console.print(f"[red]Error fetching character industry jobs: {e}[/red]")
        raise typer.Exit(code=1) from e
    end = perf_counter()
    console.print(
        f"Character industry jobs saved to {save_path} in {end - start:.2f} seconds."
    )
    if terminal:
        console.print(jobs.model_dump_json(indent=2))
