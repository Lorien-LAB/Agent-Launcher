from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "agent_launcher"


def configure_launcher_logger(log_path: str | Path) -> logging.Logger:
    """Return a single rotating logger bound to ``log_path``.

    Repeated calls reuse the existing file handler for the same path. If the
    caller switches paths, the previous handlers are closed before the new one
    is installed so tests and restarts do not leak file descriptors.
    """
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    resolved = str(path.resolve())
    existing = [
        handler
        for handler in logger.handlers
        if isinstance(handler, RotatingFileHandler)
        and str(Path(handler.baseFilename).resolve()) == resolved
    ]
    if existing:
        keep = existing[0]
        for handler in list(logger.handlers):
            if handler is keep:
                continue
            logger.removeHandler(handler)
            handler.close()
        logger.handlers[:] = [keep]
        return logger

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(
        path,
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger
