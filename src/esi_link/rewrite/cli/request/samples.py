# pyright: standard
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from esi_link.rewrite import example_requests
from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.save_text_file import save_text_file
from esi_link.rewrite.request.models import RequestGroupRoot, RequestRoot

app = typer.Typer(no_args_is_help=True)


@app.command(name="sample-requests")
def save_samples(
    ctx: typer.Context,
    output_directory: Annotated[
        Path,
        typer.Argument(
            help="Output directory path.",
        ),
    ],
    character_id: Annotated[
        int | None,
        typer.Option(
            "--character-id", help="Character ID to use for authorized request samples."
        ),
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Whether to overwrite existing files.")
    ] = False,
) -> None:
    """Save example requests to disk."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    output_directory.mkdir(parents=True, exist_ok=True)
    api_status_request = example_requests.api_status()
    saved = save_text_file(
        text=RequestRoot(root=api_status_request).model_dump_json(indent=2),
        output_dir=output_directory,
        file_name="api_status-request.json",
        overwrite=overwrite,
    )
    console.print(f"Saved api_status request: {saved}")

    server_status_request = example_requests.server_status()
    saved = save_text_file(
        text=RequestRoot(root=server_status_request).model_dump_json(indent=2),
        output_dir=output_directory,
        file_name="server_status-request.json",
        overwrite=overwrite,
    )
    console.print(f"Saved server_status request: {saved}")

    status_group_requests = example_requests.status_group()
    saved = save_text_file(
        text=RequestGroupRoot(root=status_group_requests).model_dump_json(indent=2),
        output_dir=output_directory,
        file_name="status_group-request-group.json",
        overwrite=overwrite,
    )
    console.print(f"Saved status group request: {saved}")
    if character_id is not None:
        character_attributes_request = example_requests.character_attributes(
            character_id
        )
        saved = save_text_file(
            text=RequestRoot(root=character_attributes_request).model_dump_json(
                indent=2
            ),
            output_dir=output_directory,
            file_name="character_attributes-request.json",
            overwrite=overwrite,
        )
        console.print(f"Saved character attributes request: {saved}")
