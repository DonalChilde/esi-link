from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns

from esi_link.esi_link import EsiLink
from esi_link.models import EsiLinkConfig


@dataclass
class CliConfig:
    start_time: int = perf_counter_ns()
    debug: bool = False
    verbosity: int = 1
    silent: bool = False
    auth_store_connection_string: str | None = None
    esi_link_config_path: Path | None = None
    esi_link_config: EsiLinkConfig | None = None
    esi_link: EsiLink | None = None

    def __repr__(self) -> str:
        return (
            f"CliConfig(start_time={self.start_time}, "
            f"debug={self.debug}, "
            f"verbosity={self.verbosity}, "
            f"silent={self.silent}, "
            f"auth_store_connection_string={self.auth_store_connection_string}, "
            f"esi_link_config_path={self.esi_link_config_path}, "
            f"esi_link={self.esi_link!r}"
            f")"
        )

    def __str__(self) -> str:
        return (
            f" start_time={self.start_time}\n"
            f" debug={self.debug}\n"
            f" verbosity={self.verbosity}\n"
            f" silent={self.silent}\n"
            f" auth_store_connection_string={self.auth_store_connection_string}\n"
            f" esi_link_config_path={self.esi_link_config_path}\n"
            f" esi_link={self.esi_link}\n"
        )
