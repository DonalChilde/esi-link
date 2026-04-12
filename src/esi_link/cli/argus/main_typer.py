# from esi_link.cli.main_typer import default_options  # type: ignore


# As an example.
# TODO make this a real command when argus gets split.

# @app.callback(invoke_without_command=True)
# def default_options(ctx: typer.Context):
#     """Esi Link Command Line Interface.

#     Insert pithy saying here
#     """
#     settings = get_settings()
#     setup_logging(log_dir=settings.log_directory)
#     ctx.obj = {"esi-link-settings": settings}
#     # Make an argus-settings field for now, this can be removed when Argus is split from ESI Link and has its own app.
#     argus_settings = ArgusSettings(
#         application_directory=settings.application_directory / "argus",
#         sde_directory=settings.application_directory / "argus" / "sde",
#         esi_link_settings=settings,
#     )
#     ctx.obj["argus-settings"] = argus_settings
#     logger.info(
#         f"Starting {__app_name__} v{__version__} with settings: {asdict(settings)!r}"
#     )
