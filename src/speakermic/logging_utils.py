from __future__ import annotations

from pathlib import Path
import logging
import sys


class _StreamToLogger:
    def __init__(self, level: int) -> None:
        self.level = level
        self.logger = logging.getLogger("speakermic.output")

    def write(self, message: str) -> None:
        message = message.strip()
        if message:
            self.logger.log(self.level, message)

    def flush(self) -> None:
        return


def setup_logging(app_dir: Path | None = None) -> Path:
    app_dir = app_dir or Path.cwd()
    log_path = app_dir / "speakermic.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    sys.stdout = _StreamToLogger(logging.INFO)
    sys.stderr = _StreamToLogger(logging.ERROR)
    logging.getLogger(__name__).info("Logging started: %s", log_path)
    return log_path
