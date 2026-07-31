from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .app_settings import ensure_settings_file
from .denon_client import DenonSetupClient
from .host_utils import normalize_host
from .routers import control as control_router
from .routers import setup as setup_router

UI_DIR = Path(__file__).resolve().parent / "ui"
ROOT_DIR = Path(__file__).resolve().parents[1]


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
