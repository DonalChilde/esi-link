"""Commands for working with Esi market data."""

from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from rich.console import Console
from whenever import Instant

from esi_link.cli.argus.data_factory import (
    get_market_orders_for_region,
    get_universe_market_prices,
)
from esi_link.cli.helpers import (
    get_executor_from_settings_and_schema,
    get_settings_from_context,
)
from esi_link.helpers.file_safe_string import file_safe_string
from esi_link.helpers.save_text_file import save_text_file
from esi_link.schema.schema_manager import SchemaManager
from esi_link.type_defs import LangEnum

app = typer.Typer(
    no_args_is_help=True, help="Commands for working with Esi market data."
)


@app.command()
def orders(
    ctx: typer.Context,
    region_id: Annotated[
        int, typer.Argument(help="The region ID to fetch market orders for.")
    ],
    output_dir: Annotated[
        Path, typer.Argument(help="The directory to save the market orders data to.")
    ],
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the market orders data to the terminal. Defaults to False.",
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
    """Fetch market orders for a region."""
    start = perf_counter()
    settings = get_settings_from_context(ctx)
    console = Console()
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )
    console.print(f"Fetching market orders for region {region_id}...")
    try:
        market_orders = get_market_orders_for_region(
            executor=executor, region_id=region_id, console=console, lang=lang.value
        )
        date_str = Instant.from_timestamp_nanos(market_orders.received_at).format_iso()
        file_stem = f"market_orders_region_{region_id}_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=market_orders.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
    except Exception as e:
        console.print(f"[red]Error fetching market orders: {e}[/red]")
        raise typer.Exit(code=1) from e
    end = perf_counter()
    console.print(
        f"Market orders for region {region_id} fetched and saved to {save_path} in {end - start:.2f} seconds"
    )
    if terminal:
        console.print(market_orders.model_dump_json(indent=2))


@app.command()
def universe_prices(
    ctx: typer.Context,
    output_dir: Annotated[
        Path, typer.Argument(help="The directory to save the market prices data to.")
    ],
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the market prices data to the terminal. Defaults to False.",
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
    """Fetch market prices for all items in the universe."""
    start = perf_counter()
    settings = get_settings_from_context(ctx)
    console = Console()
    schema_manager = SchemaManager(schema_directory=settings.schema_store_dir)
    stored_schema = schema_manager.get_latest_schema()
    executor = get_executor_from_settings_and_schema(
        settings=settings, schema=stored_schema.esi_schema
    )
    console.print(f"Fetching market prices for the universe...")
    try:
        market_prices = get_universe_market_prices(
            executor=executor, console=console, lang=lang.value
        )
        date_str = Instant.from_timestamp_nanos(market_prices.received_at).format_iso()
        file_stem = f"universe_market_prices_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=market_prices.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
    except Exception as e:
        console.print(f"[red]Error fetching market prices: {e}[/red]")
        raise typer.Exit(code=1) from e
    end = perf_counter()
    console.print(
        f"Market prices fetched and saved to {save_path} in {end - start:.2f} seconds"
    )
    if terminal:
        console.print(market_prices.model_dump_json(indent=2))
