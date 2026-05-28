# pyright: standard
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from whenever import Instant

from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.http_client import config_http_client
from esi_link.rewrite.helpers.save_text_file import save_text_file
from esi_link.rewrite.helpers.settings_factories import schema_cache_factory
from esi_link.rewrite.schema.schema_doc import generate_esi_schema_doc

app = typer.Typer(no_args_is_help=True)


@app.command(name="generate-doc")
def generate_doc(
    ctx: typer.Context,
    compatibility_date: Annotated[
        str | None,
        typer.Option(
            "-c",
            "--compatibility-date",
            help="Compatibility date to generate documentation for. Defaults to None. "
            "If not provided, the latest valid compatibility date will be used.",
        ),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="Output directory path. Defaults to None. If not provided, the output will "
            "be written to the terminal.",
        ),
    ] = None,
    output_file: Annotated[
        str | None,
        typer.Option(
            "-f",
            "--output-file",
            help="Output file name. Defaults to None. If not provided, the filename will "
            "be generated automatically. Ignored if output directory is not provided.",
        ),
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Whether to overwrite existing files.")
    ] = False,
) -> None:
    """Generate human readable schema documentation."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    schema_cache = schema_cache_factory(settings)
    session = config_http_client()
    with session:
        compatibility_dates = schema_cache.valid_compatibility_dates(session=session)
        if not compatibility_dates:
            console.print("No valid compatibility dates found.")
            raise typer.Exit(0)
        if (
            compatibility_date
            and compatibility_date not in compatibility_dates["compatibility_dates"]
        ):
            console.print(
                f"Compatibility date {compatibility_date} is not valid. Valid compatibility dates are:"
            )
            for date in compatibility_dates["compatibility_dates"]:
                console.print(f"- {date}")
            raise typer.Exit(0)
        if not compatibility_date:
            compatibility_date = schema_cache.latest_compatibility_date(session=session)
            if not output_directory:
                console.print(
                    f"No compatibility date provided. Using latest valid compatibility date: {compatibility_date}"
                )

        cached_schema = schema_cache.get_schema(compatibility_date, session=session)

    doc = generate_esi_schema_doc(
        cached_schema.esi_schema,
        download_date=Instant.from_timestamp(cached_schema.timestamp),
    )
    if not output_directory:
        console.print(doc)
        raise typer.Exit(0)
    if not output_file:
        output_file = (
            f"esi_schema_doc_{compatibility_date}_{cached_schema.timestamp}.md"
        )
    saved = save_text_file(
        text=doc,
        output_dir=output_directory,
        file_name=output_file,
        overwrite=overwrite,
    )
    console.print(f"Generated schema documentation written to {saved}")
