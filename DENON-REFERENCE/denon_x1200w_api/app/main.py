from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .denon_client import DenonSetupClient
from .host_utils import normalize_host
from .routers import setup as setup_router

UI_DIR = Path(__file__).resolve().parent / "ui"
ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def create_app(host: str | None = None) -> FastAPI:
    _load_dotenv(ROOT_DIR / ".env")
    raw = host or os.environ.get("DENON_HOST", "192.168.20.50")
    try:
        default_host = normalize_host(raw)
    except ValueError:
        default_host = normalize_host("192.168.20.50")

    app = FastAPI(
        title="DENON AVR MANAGER",
        description=(
            "HTTP API + UI for Denon AVR SETUP pages (tested on AVR-X1200W). "
            "AVR host is configured via DENON_HOST in `.env` (or environment). "
            "Save/Load, firmware update, network IP writes, and "
            "Audyssey Setup wizard starts are blocked."
        ),
        version="1.2.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.default_host = default_host
    app.state.denon = DenonSetupClient(default_host)
    app.include_router(setup_router.router, prefix="/api")

    if UI_DIR.is_dir():
        app.mount("/ui/assets", StaticFiles(directory=UI_DIR / "assets"), name="ui-assets")

        @app.get("/ui", include_in_schema=False)
        @app.get("/ui/", include_in_schema=False)
        def ui_index():
            return FileResponse(UI_DIR / "index.html")

    @app.get("/", include_in_schema=False)
    def root():
        if (UI_DIR / "index.html").exists():
            return RedirectResponse(url="/ui")
        return {
            "name": "DENON AVR MANAGER",
            "docs": "/docs",
            "ui": "/ui",
            "catalog": "/api/catalog",
            "health": "/api/health",
            "host_source": "DENON_HOST env / .env",
        }

    return app


app = create_app()
