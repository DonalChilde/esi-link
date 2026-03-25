"""Api entry points."""

from pathlib import Path
from typing import Literal

from esi_link.factory import EsiLinkObjectFactory
from esi_link.models_and_protocols import EsiSchema, RequestGroup, ResponseGroup


class EsiLink:
    def __init__(
        self,
        schema: EsiSchema,
        cache_directory: Path,
        credentials_file: Path,
        tokens_dir: Path,
        cache_type: Literal["diskcache", "json"] = "json",
        rate_limit_max_rate: float = 10.0,
        rate_limit_time_period: float = 1.0,
        auth_min_seconds: int = 300,
        response_handler_plugins_config: Path | None = None,
        response_group_handler_plugins_config: Path | None = None,
    ) -> None:
        """Main entry point for ESI Link."""
        self._factory = EsiLinkObjectFactory(
            schema=schema,
            cache_directory=cache_directory,
            credentials_file=credentials_file,
            tokens_dir=tokens_dir,
            cache_type=cache_type,
            rate_limit_max_rate=rate_limit_max_rate,
            rate_limit_time_period=rate_limit_time_period,
            auth_min_seconds=auth_min_seconds,
            response_handler_plugins_config=response_handler_plugins_config,
            response_group_handler_plugins_config=response_group_handler_plugins_config,
        )

    async def do_requests(self, requests: RequestGroup) -> ResponseGroup:
        """Execute a RequestGroup and return the resulting ResponseGroup."""
        group_executor = self._factory.group_executor()
        return await group_executor(requests)

    async def validate_requests(
        self, requests: RequestGroup, validation_report_path: Path | None = None
    ) -> None:
        """Validate a RequestGroup, raising an exception if it is invalid."""
        request_validator = self._factory.request_validator()
        group_validator = self._factory.request_group_validator()
        for request in requests.requests.values():
            await request_validator(request)
        group_validator(requests)

    # TODO rethink validation to be able to return separate validation failures instead
    # of just raising an exception. Maybe return a list of validation failures, or a
    # validation report object that contains the list of failures and other relevant information.


class EsiLinkTools:
    def __init__(self) -> None:
        """Tools for working with ESI Link."""
        pass

    # Tools for working with ESI Link, such as generating documentation, downloading schemas, etc.
