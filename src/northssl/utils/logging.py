import logging
from pathlib import Path
from typing import Final

LOG_FORMAT: Final[str] = "%(asctime)s %(levelname)s %(name)s %(message)s"


def _resolve_level(level: int | str) -> int:
    if isinstance(level, int):
        return level

    resolved_level = logging.getLevelName(level.upper())
    if isinstance(resolved_level, int):
        return resolved_level

    raise ValueError(f"Unsupported log level: {level}")


def configure_logging(level: int | str = logging.INFO, log_file: str | Path | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(level=_resolve_level(level), format=LOG_FORMAT, force=True, handlers=handlers)
