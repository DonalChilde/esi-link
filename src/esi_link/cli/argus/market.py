"""Commands for working with Esi market data."""

from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from rich.console import Console
from whenever import Instant

from esi_link.argus.calculations.calculate_order_summary import calculate_summaries
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
def order_summaries(
    ctx: typer.Context,
    region_id: Annotated[
        int, typer.Argument(help="The region ID to fetch market order summaries for.")
    ],
    output_dir: Annotated[
        Path,
        typer.Argument(
            help="The directory to save the market order summaries data to."
        ),
    ],
    solar_system_ids: Annotated[
        list[int] | None,
        typer.Option(
            "-s",
            "--solar-system-id",
            help="Optional solar system ID to filter orders by. If not provided, orders from all solar systems in the region will be included.",
        ),
    ] = None,
    filter_factor: Annotated[
        float,
        typer.Option(
            "-f",
            "--filter-factor",
            help="Factor used to filter outlier orders. For buy orders, only orders with price >= (highest_price / filter_factor) are included. For sell orders, only orders with price <= (lowest_price * filter_factor) are included. Defaults to 100.0.",
        ),
    ] = 100.0,
    terminal: Annotated[
        bool,
        typer.Option(
            "--terminal",
            help="Whether to print the market order summaries data to the terminal. Defaults to False.",
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
    """Fetch market order summaries for a region and type, optionally additional summaries filtered by solar system."""
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
        print(
            f"Calculating {len(market_orders.orders)} order summaries for region {region_id}..."
        )
        region_summaries = calculate_summaries(
            region_orders=market_orders, filter_factor=filter_factor
        )
        date_str = Instant.from_timestamp_nanos(market_orders.received_at).format_iso()
        file_stem = f"market_order_summaries_region_{region_id}_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=region_summaries.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
    except Exception as e:
        console.print(f"[red]Error fetching market orders: {e}[/red]")
        raise typer.Exit(code=1) from e
    end = perf_counter()
    console.print(
        f"Market order summaries for region {region_id} fetched and saved to {save_path} in {end - start:.2f} seconds"
    )
    for solar_system_id in solar_system_ids or []:
        console.print(
            f"Calculating order summaries for solar system {solar_system_id} in region {region_id}..."
        )
        solar_system_summaries = calculate_summaries(
            region_orders=market_orders,
            solar_system_id=solar_system_id,
            filter_factor=filter_factor,
        )
        file_stem = f"market_order_summaries_region_{region_id}_solar_system_{solar_system_id}_{date_str}"
        file_stem = file_safe_string(file_stem)
        save_path = save_text_file(
            text=solar_system_summaries.model_dump_json(indent=2),
            output_dir=output_dir,
            file_name=f"{file_stem}.json",
            overwrite=overwrite,
        )
        console.print(
            f"Market order summaries for solar system {solar_system_id} in region {region_id} fetched and saved to {save_path} in {end - start:.2f} seconds"
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
