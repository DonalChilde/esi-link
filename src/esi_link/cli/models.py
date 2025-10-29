"""CLI configuration model for ESI Link."""

from dataclasses import dataclass
from time import perf_counter_ns

from esi_link.esi_link import EsiLink
from esi_link.models import EsiSchema
from esi_link.settings import EsiLinkSettings


@dataclass
class CliConfig:
    settings: EsiLinkSettings
    start_time: int = perf_counter_ns()
    debug: bool = False
    verbosity: int = 1
    silent: bool = False

    esi_schema: EsiSchema | None = None
    esi_link: EsiLink | None = None

    def __repr__(self) -> str:
        """Represent the CLI configuration."""
        return (
            f"CliConfig(start_time={self.start_time}, "
            f"debug={self.debug}, "
            f"verbosity={self.verbosity}, "
            f"silent={self.silent}, "
            f"settings={self.settings!r}, "
            f"esi_schema={self.esi_schema!s}, "
            f"esi_link={self.esi_link!r}"
            f")"
        )

    def __str__(self) -> str:
        """String representation of the CLI configuration."""
        return (
            f" start_time={self.start_time}\n"
            f" debug={self.debug}\n"
            f" verbosity={self.verbosity}\n"
            f" silent={self.silent}\n"
            f" settings={self.settings}\n"
            f" esi_schema={self.esi_schema}\n"
            f" esi_link={self.esi_link}\n"
        )
