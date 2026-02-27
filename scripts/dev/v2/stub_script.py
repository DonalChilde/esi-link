# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

from pathlib import Path

from esi_link.v2.logging_config import setup_logging

SCRIPT_NAME = "stub_script"


def main() -> None:
    print("Hello from esi_test.py!")


if __name__ == "__main__":
    log_dir = Path(f"./logs/script_logs/{SCRIPT_NAME}").resolve()
    print(f"Logging to {log_dir}")
    setup_logging(log_dir)
    main()
