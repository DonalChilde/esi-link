"""CLI commands for listing cached ESI schemas."""

import typer
from rich.console import Console
from rich.markdown import Markdown

from esi_link.rewrite.cli.helpers import get_esi_link_settings_from_context
from esi_link.rewrite.helpers.settings_factories import schema_cache_factory
from esi_link.rewrite.schema.schema_cache import CachedSchemaPath

app = typer.Typer(no_args_is_help=True)


@app.command()
def list_cached(ctx: typer.Context) -> None:
    """List all cached schemas."""
    console = Console()
    settings = get_esi_link_settings_from_context(ctx)
    schema_cache = schema_cache_factory(settings)
    cached_schemas = schema_cache.list_cached_schemas()
    if not cached_schemas:
        console.print("No cached schemas found.")
        raise typer.Exit(0)
    console.print("Cached Schemas:")
    schema_ttl = schema_cache.schema_ttl
    console.print(Markdown(_markdown_format_cached_schemas(cached_schemas, schema_ttl)))


def _markdown_format_cached_schemas(
    cached_schemas: dict[str, CachedSchemaPath], ttl: int
) -> str:
    # A markdown table with columns for the schema name, path, and time until expiration in days:hours:seconds. If the schema is expired, show "Expired" in the time until expiration column.
    if not cached_schemas:
        return "No cached schemas found."
    lines: list[str] = [
        "| Schema Name | Time Until Expiration | Path |",
        "|-------------|-----------------------|------|",
    ]
    for schema_name, cached_schema in cached_schemas.items():
        expires_in_seconds = cached_schema.expires_in(ttl)
        if expires_in_seconds < 0:
            expires_in = "Expired"
        else:
            days, remainder = divmod(expires_in_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            expires_in = f"{days}d {hours}h {minutes}m {seconds}s"
        lines.append(f"| {schema_name} | {expires_in} | {cached_schema.file_path} |")
    return "\n".join(lines)
