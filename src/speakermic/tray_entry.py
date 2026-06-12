from __future__ import annotations

from pathlib import Path
import os
import sys

from speakermic.cli import main
from speakermic.logging_utils import setup_logging


def run() -> int:
    app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path.cwd()
    os.chdir(app_dir)
    setup_logging(app_dir)
    return main(["tray"])


if __name__ == "__main__":
    raise SystemExit(run())
