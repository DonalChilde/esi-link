"""ESI Link CLI - Requests Commands."""

import typer

from esi_link.cli.helpers import get_settings_from_context

app = typer.Typer(no_args_is_help=True)

# Support loading and saving requests in JSON and YAML formats


@app.command()
def execute(ctx: typer.Context):
    """Execute the ESI Link CLI command."""
    # Loads a RequestGroup from a file and executes it.
    # Display options -
    # - json to terminal
    # - summary to terminal
    # - brief summary to terminal
    settings = get_settings_from_context(ctx)
    # Here you would add the logic to execute the command using the settings
    print(f"Executing with settings: {settings}")


@app.command()
def validate(ctx: typer.Context):
    """Validate the ESI Link CLI command."""
    # Validates a RequestGroup from a file and checks for any issues.
    settings = get_settings_from_context(ctx)
    # Here you would add the logic to validate the command using the settings
    print(f"Validating with settings: {settings}")


@app.command()
def group_stub(ctx: typer.Context):
    """Group stub command."""
    # output a stub RequestGroup to a file or terminal for use as a template.
    # Option for JSON or YAML output.

    settings = get_settings_from_context(ctx)
    # Here you would add the logic for the group stub command using the settings
    print(f"Group stub with settings: {settings}")


@app.command()
def stub(ctx: typer.Context):
    """Stub command."""
    # output a stub Request to a file or terminal for use as a template.
    # Option for JSON or YAML output.
    # option to specify operation_id, and have parameters generated.

    settings = get_settings_from_context(ctx)
    # Here you would add the logic for the stub command using the settings
    print(f"Stub with settings: {settings}")


@app.command()
def handlers(ctx: typer.Context):
    """Handlers command."""
    # List the available handlers for use in the RequestGroups, and their parameters.
    # Get the doc string from the handler for details?
    settings = get_settings_from_context(ctx)
    # Here you would add the logic for the handlers command using the settings
    print(f"Handlers with settings: {settings}")
