# Planned refactors

## NOW

### FIXME
- report generation for blueprints and jobs.
  - inputs need to be updated to use new esd paradigm
  - cli loads previously saved data for report?
  - Uses name cache.
    - make a settings entry for argus data, filename lookup, etc.
  - avoid network calls in the report generation functions. If necessary, collect names first and pass into the report function.

#### esi-link
- Currently esi-link (validation?) fails if no creds are present, even if the request
  being made does not require authentication. We should refactor the code so that
  authentication is only attempted when required, and that the absence of credentials does
  not cause failures for non-authenticated requests. This may involve refactoring the
  API client code to separate the authentication logic from the request logic, and to
  only attempt authentication when making requests that require it. This would improve
  the usability of the application for users who do not need authentication, and would
  also make it more robust in cases where credentials are not available or not needed.

### ADD
- argus - Add market-hub-report command, to pull orders for the five (?) hub regions, and give summaries for region and hub system. Include report order count and isk volume per system.
- as location names finer than solarsystem are a pita, but dont change that much, get them from ESI and cache them. May need to wait for sqlite database.
 - make command to collect all the names? maybe split to planets, moons, stations, etc?

### CHANGE
- esi-link EsiLinkSettings should contain an EsiAuthSettings instance to hold those settings. 
  - EsiLinkSettingsPydantic can hold individual esi-auth settings, and they are resolved in get_settings()
  - esi-link.get_settings will construct an EsiAuthSettingsPydantic object, and feed it to esi-auth.get_settings()
- esi-link Refactor object models and functions for esi-link
  - Move to a functional paradigm
  - immutable returns
  - dataclass models with RootModel serializers
  - return tuple[dict[uuid,response], dict[uuid,response]] for success failure.
  - re functional example at https://www.youtube.com/watch?v=A7lGxqCuFN4

### General

 - It is the responsibility of the top-level cli callback to call get_settings, and to
   add the required settings and sub-settings to the ctx.obj, so that they can be accessed
   by the subcommands. This way we can ensure that the settings are loaded and available
   for all subcommands, and that the settings loading logic is centralized in one place.

```python
def example_callback(ctx: typer.Context):
    """Example callback function for the CLI."""
    settings = get_settings()
    ctx.obj = {"esi-link-settings": settings}
    # a copy of the esi-auth settings is added under the key expected by the esi-auth cli commands.
    ctx.obj["esi-auth-settings"] = settings.esi_auth_settings
```
- Document the design philosophy behind the dual settings classes, and why its a benefit for
  combining separate projects with a cli.
- Standardize the location of project constants like application name, version, url,
  and default application directory, so that they can be easily imported and used across
  modules without circular imports or duplication.
- Standardize the location of default settings values, like urls.
- Standardize to use factory functions that take a settings object where appropriate to simplify object creation.
- Standardize and document the settings paradigm across all the projects.
- Update env file generation function for all projects


#### esi-link


- Examine esi-auth usage, and make sure that creating the access api classes from EsiAuthSettings
  is straightforward and well supported by the settings class design. The goal is to
  make it as easy as possible to use esi-auth with ESI Link, and to have a clear
  separation of concerns between the two modules.



#### esi-auth







#### argus

- Add display and warning about the build_number of the currently supported sde dataset,
  the current schema (online) and the dataset to import.

- Add a separate database for SDE data.
- Add a separate database for market history
- Create audit classes and functions for industry calculations.
  - the goal is to be able to display the work after calculation.
  - To save memory, mayb the top level can collect things like facility profile, system indexes, and names to typeID.
  - This could also be similar to a "project" type build info collection, where parts are planned to be made in different locations.


- Argus CLI commands only need the value added commands, eg. no need for a raw regional orders cli command, That could be just a regular esi-link command.
  But reports, and order summaries are appropriate, and the raw data could be saved then too....


## FUTURE

### esi-link
- Add an sqlite based cache option, backed with raw sql and dataclasses. Do this sooner as a learning project looking towards a more complicated database for argus.

### esi-auth

### argus
- Add sqlite database to store application information between runs.




