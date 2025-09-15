"""Command-line interface."""

import logging
from dataclasses import dataclass
from time import perf_counter, perf_counter_ns
from typing import Annotated

import typer

from esi_link import CONFIG
from esi_link.config import CacheType
from esi_link.esi_client.esi_client import EsiClient
from esi_link.esi_client.esi_file_cache import EsiFileCache
from esi_link.esi_client.esi_memory_cache import EsiMemoryCache
from esi_link.esi_client.link_cache_protocol import LinkCacheProtocol
from esi_link.esi_schema.esi_api import EsiApi
from esi_link.esi_schema.esi_api_protocol import EsiApiProtocol
from esi_link.esi_schema.schema_store import SchemaStore
from esi_link.helpers.indent_lines import indent_lines

from .esi_cache import app as cache_app
from .esi_query import app as query_app
from .esi_schema import app as schema_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(schema_app, name="schema", help="Manage ESI schema.")
app.add_typer(query_app, name="query", help="Query ESI data.")
app.add_typer(cache_app, name="cache", help="Manage ESI cache.")


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass
class CliConfig:
    start_time: int = perf_counter_ns()
    debug: bool = False
    verbosity: int = 1
    schema_store: SchemaStore | None = None
    esi_api: EsiApiProtocol | None = None
    cache: LinkCacheProtocol | None = None
    client: EsiClient | None = None
    silent: bool = False

    def __repr__(self) -> str:
        return (
            f"CliConfig(start_time={self.start_time}, "
            f"debug={self.debug}, "
            f"verbosity={self.verbosity}, "
            f"schema_store={self.schema_store}, "
            f"silent={self.silent})"
        )

    def __str__(self) -> str:
        return (
            f" start_time={self.start_time}\n"
            f" debug={self.debug}\n"
            f" verbosity={self.verbosity}\n"
            f" schema_store={self.schema_store}\n"
            f" silent={self.silent}"
        )


@app.callback(invoke_without_command=True)
def default_options(
    ctx: typer.Context,
    debug: Annotated[bool, typer.Option(help="Enable debug output.")] = False,
    verbosity: Annotated[int, typer.Option("-v", help="Verbosity.", count=True)] = 1,
    silent: Annotated[
        bool,
        typer.Option(help="Enable silent mode. Only results and errors will be shown."),
    ] = False,
):
    """Esi Link Command Line Interface.

    Insert pithy saying here
    """
    ctx.ensure_object(CliConfig)
    ctx.obj.start_time = perf_counter_ns()
    ctx.obj.debug = debug
    ctx.obj.verbosity = verbosity
    ctx.obj.silent = silent
    init_config(ctx)

    if ctx.obj.schema_store:
        schema_msg = "Schema loaded successfully."
    else:
        schema_msg = "No schema found. Try `esi-link schema update`."

    welcome = f"""
    Welcome to Esi Link! Your CLI interface to the Eve Online ESI api.
    Application data located at {CONFIG.app_dir}
    Schema status: {schema_msg}
    """
    if not ctx.obj.silent:
        typer.echo(welcome)

    if ctx.obj.verbosity > 1:
        typer.echo("CLI configuration:")
        typer.echo(f"{indent_lines(str(ctx.obj), indent=2)}")
        typer.echo("App configuration:")
        typer.echo(f"{indent_lines(str(CONFIG), indent=2)}")


def load_schema(ctx: typer.Context) -> SchemaStore:
    """Load the ESI schema."""
    store_path = CONFIG.schema_dir / "schema_store.json"
    if not store_path.exists():
        store = SchemaStore.from_download(store_path=store_path)
        typer.echo(
            f"Schema downloaded and store created on {store.download_date}, saved to {store_path}"
        )
        return store
    store = SchemaStore(store_path=store_path)
    typer.echo(
        f"Schema store with download date of {store.download_date} loaded from {store_path}"
    )
    return store


def init_config(ctx: typer.Context) -> None:
    """Initialize the CLI configuration with cache and client."""
    start = perf_counter()
    ctx.obj.schema_store = load_schema(ctx)
    ctx.obj.esi_api = EsiApi.from_schema_store(ctx.obj.schema_store)
    # TODO option to clear cache entries older than X days
    if CONFIG.cache_type == CacheType.FILE:
        ctx.obj.cache = EsiFileCache(file_path=CONFIG.cache_file)
    elif CONFIG.cache_type == CacheType.MEMORY:
        ctx.obj.cache = EsiMemoryCache()
    elif CONFIG.cache_type == CacheType.SQLITE:
        raise NotImplementedError("SQLite cache is not implemented yet.")
    else:
        raise ValueError(f"Unknown cache type: {CONFIG.cache_type}")

    ctx.obj.client = EsiClient(
        esi_api=ctx.obj.esi_api,
        cache=ctx.obj.cache,
        max_concurrent_requests=50,
    )
    logger.info(f"EsiClient initialized in {perf_counter() - start:.2f} seconds.")


if __name__ == "__main__":
    app()
