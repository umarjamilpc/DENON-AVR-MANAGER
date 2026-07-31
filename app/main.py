from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .app_settings import ensure_settings_file, load_settings
from .denon_client import DenonSetupClient
from .denon_control import SUPPORTED_MODELS, DenonControl
from .denon_power import read_main_zone_power
from .host_utils import normalize_host
from .routers import control as control_router
from .routers import setup as setup_router

UI_DIR = Path(__file__).resolve().parent / "ui"
ROOT_DIR = Path(__file__).resolve().parents[1]
log = logging.getLogger("denon.preload")


def _settings_model() -> str:
    m = str(load_settings().get("avr_model") or "AVR-X1200W")
    return m if m in SUPPORTED_MODELS else "AVR-X1200W"


def _run_control_preload(app: FastAPI) -> None:
    """Background: query full AVR status once into the shared telnet cache."""
    state: Dict[str, Any] = getattr(app.state, "control_preload", {})
    state.update({"status": "running", "started_at": time.time(), "error": None})
    app.state.control_preload = state
    try:
        http = DenonSetupClient(app.state.default_host)
        ctrl = DenonControl(http)
        app.state.denon_control = ctrl
        power = None
        try:
            power = read_main_zone_power(http)
        except Exception:
            power = None
        model = _settings_model()
        snap = ctrl.preload_all_status(model=model, power=power)
        app.state.control_preload = {
            "status": "ready",
            "started_at": state.get("started_at"),
            "finished_at": time.time(),
            "model": model,
            "entity_count": len(snap.get("entities") or {}),
            "queried": len(snap.get("queried") or []),
            "errors": list(snap.get("errors") or [])[:12],
            "transport": snap.get("transport"),
            "error": None,
        }
        log.info(
            "Control preload ready: %s entities, %s queries",
            app.state.control_preload["entity_count"],
            app.state.control_preload["queried"],
        )
    except Exception as e:
        log.warning("Control preload failed: %s", e)
        app.state.control_preload = {
            "status": "error",
            "started_at": state.get("started_at"),
            "finished_at": time.time(),
            "error": str(e),
            "entity_count": 0,
            "queried": 0,
            "errors": [str(e)],
        }


def create_app(host: str | None = None) -> FastAPI:
    # Host comes from the process environment (Docker Compose / systemd / shell).
    # No .env file is used.
    raw = host or os.environ.get("DENON_HOST")
    if not raw:
        raise RuntimeError(
            "DENON_HOST is required. Set it in docker-compose.yml (environment) "
            "or export it in your shell, e.g. DENON_HOST=192.168.1.50"
        )
    try:
        default_host = normalize_host(raw)
    except ValueError as e:
        raise RuntimeError(f"Invalid DENON_HOST={raw!r}: {e}") from e

    # Create /data/app-settings.json (or local data/) with defaults if missing.
    ensure_settings_file()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.control_preload = {"status": "pending", "error": None}
        thread = threading.Thread(
            target=_run_control_preload,
            args=(app,),
            name="control-preload",
            daemon=True,
        )
        thread.start()
        yield

    app = FastAPI(
        title="DENON AVR MANAGER",
        description=(
            "HTTP API + UI for Denon AVR SETUP pages (tested on AVR-X1200W). "
            "AVR host is configured via the DENON_HOST environment variable "
            "(set in docker-compose.yml). "
            "Works behind HTTP or HTTPS reverse proxies (e.g. Nginx Proxy Manager). "
            "Save/Load, firmware update, network IP writes, and "
            "Audyssey Setup wizard starts are blocked by default safety policy."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    # Trust X-Forwarded-* from NPM / Traefik / Caddy (HTTP and HTTPS frontends).
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.default_host = default_host
    app.state.denon = DenonSetupClient(default_host)
    app.state.control_preload = {"status": "pending", "error": None}
    app.include_router(setup_router.router, prefix="/api")
    app.include_router(control_router.router, prefix="/api")

    def spa_index():
        return FileResponse(UI_DIR / "index.html")

    if UI_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=UI_DIR / "assets"), name="assets")
        # Web UI at site root — no /ui path, no redirect.
        app.add_api_route(
            "/",
            spa_index,
            methods=["GET"],
            include_in_schema=False,
            response_model=None,
        )

    return app


app = create_app()
