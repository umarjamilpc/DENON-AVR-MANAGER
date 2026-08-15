"""Central logging setup for Docker console and local runs."""

from __future__ import annotations

import logging
import os
import sys


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name) or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "debug",
    }


def configure_logging() -> None:
    """Configure root + denon loggers once (idempotent)."""
    if getattr(configure_logging, "_done", False):
        return

    level_name = str(os.environ.get("LOG_LEVEL") or "INFO").strip().upper()
    if _env_truthy("DEBUG") or _env_truthy("APP_DEBUG"):
        level_name = "DEBUG"
    level = getattr(logging, level_name, logging.INFO)

    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("denon", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(level)

    configure_logging._done = True  # type: ignore[attr-defined]
