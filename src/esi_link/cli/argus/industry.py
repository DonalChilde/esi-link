import asyncio
import json
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from rich.console import Console
from whenever import Instant

from esi_link.argus import requests as argus_requests
from esi_link.argus.calculations.eiv import calculate_eivs
from esi_link.cli.argus.helpers import (
    check_for_sde_before_use,
    get_argus_settings_from_context,
)
from esi_link.cli.helpers import get_executor_from_settings_and_schema
from esi_link.helpers.file_safe_string import file_safe_string
from esi_link.helpers.save_text_file import save_text_file
from esi_link.type_defs import LangEnum

app = typer.Typer(
    no_args_is_help=True, help="Commands for working with Esi market data."
)


@app.command()
def eivs(
    ctx: typer.Context,
    output_dir: Annotated[
        Path, typer.Argument(help="The directory to save the eiv data to.")
    ],
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the eiv data to the terminal. Defaults to False.",
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
    """Calculate the EIV for all manufactured items."""
    start = perf_counter()
    argus_settings = get_argus_settings_from_context(ctx)
    esi_link_settings = argus_settings.esi_link_settings
    console = Console()
    executor = get_executor_from_settings_and_schema(settings=esi_link_settings)
    check_for_sde_before_use(argus_settings=argus_settings, console=console)
    sde_loader = argus_settings.esd_settings.sde_loader()
    boms = sde_loader.derived_datasets.bills_of_materials()
    console.print(f"Fetching market prices for the universe...")
    try:
        prices_task = argus_requests.universe_prices(esi_link=executor, lang=lang.value)
        market_prices = asyncio.run(prices_task)
        eiv_results = calculate_eivs(boms=boms, prices=market_prices)

        date_str = Instant.from_timestamp_nanos(market_prices.received_at).format_iso()
        file_stem = f"eivs_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=json.dumps(eiv_results, indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
    except Exception as e:
        console.print(f"[red]Error calculating EIVs: {e}[/red]")
        raise typer.Exit(code=1) from e
    end = perf_counter()
    console.print(
        f"EIVs calculated and saved to {save_path} in {end - start:.2f} seconds"
    )
    if terminal:
        console.print(json.dumps(eiv_results, indent=2))
