"""Customizable Dashboard API — sections and favourite control widgets."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import db
from ..app_settings import load_settings
from ..denon_client import DenonSetupClient
from ..denon_control import SUPPORTED_MODELS, DenonControl
from ..host_utils import host_label
from ..protocol_loader import normalize_layout

router = APIRouter(tags=["dashboard"])


def _model() -> str:
    m = str(load_settings().get("avr_model") or "AVR-X1200W")
    return m if m in SUPPORTED_MODELS else "AVR-X1200W"


def _enrich_dashboard(data: Dict[str, Any], request_base: str) -> Dict[str, Any]:
    """Attach catalog control definitions for each widget (less + more)."""
    settings = load_settings()
    http = DenonSetupClient(request_base)
    ctrl = DenonControl(http)
    less = ctrl.catalog(
        model=_model(), show_zone2=True, show_zone3=True, layout="less"
    )
    more = ctrl.catalog(
        model=_model(), show_zone2=True, show_zone3=True, layout="more"
    )
    by_layout = {
        "less": {str(c.get("id")): c for c in less.get("controls") or []},
        "more": {str(c.get("id")): c for c in more.get("controls") or []},
    }
    sections_out = []
    for sec in data.get("sections") or []:
        widgets_out = []
        for w in sec.get("widgets") or []:
            layout = normalize_layout(w.get("control_layout") or "less")
            cid = str(w.get("control_id") or "")
            control = by_layout.get(layout, {}).get(cid) or by_layout["more"].get(cid)
            widgets_out.append({**w, "control": control, "control_layout": layout})
        sections_out.append({**sec, "widgets": widgets_out})
    return {
        "ok": True,
        "host": host_label(request_base),
        "model": _model(),
        "settings_layout": normalize_layout(settings.get("control_grouping")),
        "sections": sections_out,
        "db_path": str(db.db_path()),
    }


def _base(request: Request) -> str:
    return request.app.state.default_host


class DashboardBody(BaseModel):
    sections: List[Dict[str, Any]] = Field(default_factory=list)


class SectionBody(BaseModel):
    title: str = "New section"


class RenameBody(BaseModel):
    title: str


class WidgetBody(BaseModel):
    section_id: str
    control_id: str
    control_layout: str = "less"


@router.get("/dashboard")
def get_dashboard(request: Request) -> Dict[str, Any]:
    db.init_db()
    return _enrich_dashboard(db.load_dashboard(), _base(request))


@router.put("/dashboard")
def put_dashboard(request: Request, body: DashboardBody) -> Dict[str, Any]:
    try:
        data = db.replace_dashboard({"sections": body.sections})
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _enrich_dashboard(data, _base(request))


@router.post("/dashboard/sections")
def create_section(request: Request, body: SectionBody) -> Dict[str, Any]:
    data = db.add_section(body.title)
    return _enrich_dashboard(data, _base(request))


@router.patch("/dashboard/sections/{section_id}")
def patch_section(
    request: Request, section_id: str, body: RenameBody
) -> Dict[str, Any]:
    data = db.rename_section(section_id, body.title)
    return _enrich_dashboard(data, _base(request))


@router.delete("/dashboard/sections/{section_id}")
def remove_section(request: Request, section_id: str) -> Dict[str, Any]:
    data = db.delete_section(section_id)
    return _enrich_dashboard(data, _base(request))


@router.post("/dashboard/widgets")
def create_widget(request: Request, body: WidgetBody) -> Dict[str, Any]:
    try:
        data = db.add_widget(body.section_id, body.control_id, body.control_layout)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _enrich_dashboard(data, _base(request))


@router.delete("/dashboard/widgets/{widget_id}")
def remove_widget(request: Request, widget_id: str) -> Dict[str, Any]:
    data = db.delete_widget(widget_id)
    return _enrich_dashboard(data, _base(request))


@router.get("/dashboard/catalog")
def dashboard_catalog(request: Request) -> Dict[str, Any]:
    """Both less and more catalogs for the widget picker."""
    http = DenonSetupClient(_base(request))
    ctrl = DenonControl(http)
    model = _model()
    return {
        "ok": True,
        "model": model,
        "less": ctrl.catalog(
            model=model, show_zone2=True, show_zone3=True, layout="less"
        ),
        "more": ctrl.catalog(
            model=model, show_zone2=True, show_zone3=True, layout="more"
        ),
    }
