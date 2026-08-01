"""Customizable Dashboard API — sections and favourite control widgets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from .. import db
from .. import icons_store
from ..app_settings import load_settings
from ..denon_client import DenonSetupClient
from ..denon_control import SUPPORTED_MODELS, DenonControl
from ..host_utils import host_label
from ..protocol_loader import normalize_layout

router = APIRouter(tags=["dashboard"])

# Curated MDI names for the icon picker (full pack is loaded via local webfont).
MDI_SUGGESTIONS = [
    "power",
    "power-standby",
    "power-on",
    "power-off",
    "volume-high",
    "volume-medium",
    "volume-low",
    "volume-off",
    "volume-mute",
    "speaker",
    "speaker-off",
    "amplifier",
    "home",
    "home-outline",
    "television",
    "television-off",
    "cast",
    "cast-off",
    "remote",
    "gamepad-variant",
    "movie",
    "music",
    "music-off",
    "headphones",
    "surround-sound",
    "import",
    "export",
    "play",
    "pause",
    "stop",
    "skip-next",
    "skip-previous",
    "lightbulb",
    "lightbulb-outline",
    "lightbulb-on",
    "lightbulb-off",
    "ceiling-light",
    "fan",
    "fan-off",
    "thermometer",
    "water",
    "weather-sunny",
    "weather-night",
    "lock",
    "lock-open",
    "door",
    "door-open",
    "window-closed",
    "window-open",
    "radiator",
    "air-conditioner",
    "cog",
    "cog-outline",
    "tune",
    "information",
    "information-outline",
    "alert",
    "check-circle",
    "close-circle",
    "plus",
    "minus",
    "arrow-up",
    "arrow-down",
    "arrow-left",
    "arrow-right",
    "menu",
    "dots-horizontal",
    "star",
    "star-outline",
    "heart",
    "heart-outline",
    "flash",
    "flash-off",
    "battery",
    "battery-outline",
    "wifi",
    "wifi-off",
    "bluetooth",
    "bluetooth-off",
    "cellphone",
    "tablet",
    "monitor",
    "monitor-speaker",
]


def _model() -> str:
    m = str(load_settings().get("avr_model") or "AVR-X1200W")
    return m if m in SUPPORTED_MODELS else "AVR-X1200W"


def _default_icons_for(control_id: str) -> Dict[str, str]:
    defaults = {
        "pw_power": ("mdi:power", "mdi:power-standby"),
        "zm_main": ("mdi:amplifier", "mdi:amplifier-off"),
        "z2_power": ("mdi:speaker", "mdi:speaker-off"),
        "z3_power": ("mdi:speaker", "mdi:speaker-off"),
        "mu_mute": ("mdi:volume-off", "mdi:volume-high"),
        "z2_mute": ("mdi:volume-off", "mdi:volume-high"),
        "si_select": ("mdi:import", "mdi:import"),
        "ms_select": ("mdi:surround-sound", "mdi:surround-sound"),
        "mv_master": ("mdi:volume-high", "mdi:volume-medium"),
    }
    on, off = defaults.get(control_id, ("mdi:tune", "mdi:tune"))
    return {"icon_on": on, "icon_off": off}


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
            defaults = _default_icons_for(cid)
            icon_on = str(w.get("icon_on") or "") or defaults["icon_on"]
            icon_off = str(w.get("icon_off") or "") or defaults["icon_off"]
            color_on = str(w.get("color_on") or "") or "#e8eef2"
            color_off = str(w.get("color_off") or "") or "#3a4248"
            widgets_out.append(
                {
                    **w,
                    "control": control,
                    "control_layout": layout,
                    "icon_on": icon_on,
                    "icon_off": icon_off,
                    "color_on": color_on,
                    "color_off": color_off,
                    "icon_on_resolved": icons_store.resolve_icon_ref(icon_on),
                    "icon_off_resolved": icons_store.resolve_icon_ref(icon_off),
                }
            )
        sections_out.append({**sec, "widgets": widgets_out})
    by_id = {str(s["id"]): s for s in sections_out}
    layouts_out = []
    for ly in data.get("layouts") or []:
        secs = []
        for sec in ly.get("sections") or []:
            sid = str(sec.get("id") or "")
            secs.append(by_id.get(sid) or {**sec, "widgets": sec.get("widgets") or []})
        layouts_out.append({**ly, "sections": secs})
    return {
        "ok": True,
        "host": host_label(request_base),
        "model": _model(),
        "settings_layout": normalize_layout(settings.get("control_grouping")),
        "layouts": layouts_out,
        "sections": sections_out,
        "db_path": str(db.db_path()),
    }


def _base(request: Request) -> str:
    return request.app.state.default_host


class DashboardBody(BaseModel):
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    layouts: Optional[List[Dict[str, Any]]] = None


class SectionBody(BaseModel):
    title: str = "New section"
    layout_id: Optional[str] = None


class LayoutBody(BaseModel):
    stack: str = "horizontal"


class LayoutPatchBody(BaseModel):
    stack: Optional[str] = None


class SectionPatchBody(BaseModel):
    title: Optional[str] = None
    stack: Optional[str] = None
    shape: Optional[str] = None  # legacy alias → stack
    size: Optional[str] = None
    collapsed: Optional[bool] = None
    layout_id: Optional[str] = None


class WidgetBody(BaseModel):
    section_id: str
    control_id: str
    control_layout: str = "less"
    shape: str = "square"
    size: str = "md"
    icon_on: str = ""
    icon_off: str = ""
    color_on: str = ""
    color_off: str = ""


class WidgetPatchBody(BaseModel):
    shape: Optional[str] = None
    size: Optional[str] = None
    icon_on: Optional[str] = None
    icon_off: Optional[str] = None
    color_on: Optional[str] = None
    color_off: Optional[str] = None
    control_layout: Optional[str] = None


class IconUrlBody(BaseModel):
    url: str
    name: str = ""


@router.get("/dashboard")
def get_dashboard(request: Request) -> Dict[str, Any]:
    db.init_db()
    return _enrich_dashboard(db.load_dashboard(), _base(request))


@router.put("/dashboard")
def put_dashboard(request: Request, body: DashboardBody) -> Dict[str, Any]:
    try:
        data = db.replace_dashboard(
            {"sections": body.sections, "layouts": body.layouts}
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _enrich_dashboard(data, _base(request))


@router.post("/dashboard/layouts")
def create_layout(request: Request, body: LayoutBody) -> Dict[str, Any]:
    data = db.add_layout(body.stack)
    return _enrich_dashboard(data, _base(request))


@router.patch("/dashboard/layouts/{layout_id}")
def patch_layout(
    request: Request, layout_id: str, body: LayoutPatchBody
) -> Dict[str, Any]:
    data = db.update_layout(layout_id, {"stack": body.stack})
    return _enrich_dashboard(data, _base(request))


@router.delete("/dashboard/layouts/{layout_id}")
def remove_layout(request: Request, layout_id: str) -> Dict[str, Any]:
    data = db.delete_layout(layout_id)
    return _enrich_dashboard(data, _base(request))


@router.post("/dashboard/sections")
def create_section(request: Request, body: SectionBody) -> Dict[str, Any]:
    data = db.add_section(body.title, layout_id=body.layout_id)
    return _enrich_dashboard(data, _base(request))


@router.patch("/dashboard/sections/{section_id}")
def patch_section(
    request: Request, section_id: str, body: SectionPatchBody
) -> Dict[str, Any]:
    data = db.update_section(
        section_id,
        {
            "title": body.title,
            "stack": body.stack,
            "shape": body.shape,
            "size": body.size,
            "collapsed": body.collapsed,
            "layout_id": body.layout_id,
        },
    )
    return _enrich_dashboard(data, _base(request))


@router.delete("/dashboard/sections/{section_id}")
def remove_section(request: Request, section_id: str) -> Dict[str, Any]:
    data = db.delete_section(section_id)
    return _enrich_dashboard(data, _base(request))


@router.post("/dashboard/widgets")
def create_widget(request: Request, body: WidgetBody) -> Dict[str, Any]:
    try:
        defaults = _default_icons_for(body.control_id)
        data = db.add_widget(
            body.section_id,
            body.control_id,
            body.control_layout,
            shape=body.shape,
            size=body.size,
            icon_on=body.icon_on or defaults["icon_on"],
            icon_off=body.icon_off or defaults["icon_off"],
            color_on=body.color_on,
            color_off=body.color_off,
        )
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _enrich_dashboard(data, _base(request))


@router.patch("/dashboard/widgets/{widget_id}")
def patch_widget(
    request: Request, widget_id: str, body: WidgetPatchBody
) -> Dict[str, Any]:
    data = db.update_widget(
        widget_id,
        {
            "shape": body.shape,
            "size": body.size,
            "icon_on": body.icon_on,
            "icon_off": body.icon_off,
            "color_on": body.color_on,
            "color_off": body.color_off,
            "control_layout": body.control_layout,
        },
    )
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


@router.get("/dashboard/icons")
def list_icons() -> Dict[str, Any]:
    return {
        "ok": True,
        "custom": icons_store.list_icons(),
        "mdi_suggestions": [f"mdi:{n}" for n in MDI_SUGGESTIONS],
    }


@router.post("/dashboard/icons/upload")
async def upload_icon(
    file: UploadFile = File(...),
    name: str = Form(""),
) -> Dict[str, Any]:
    data = await file.read()
    try:
        icon = icons_store.save_icon_bytes(
            data,
            name=name or (file.filename or "icon"),
            filename_hint=file.filename or "",
            content_type=file.content_type or "",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "icon": icon}


@router.post("/dashboard/icons/from-url")
def icon_from_url(body: IconUrlBody) -> Dict[str, Any]:
    try:
        icon = icons_store.save_icon_from_url(body.url, body.name)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "icon": icon}


@router.delete("/dashboard/icons/{icon_id}")
def remove_icon(icon_id: str) -> Dict[str, Any]:
    try:
        icons_store.delete_icon(icon_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return {"ok": True, "custom": icons_store.list_icons()}
