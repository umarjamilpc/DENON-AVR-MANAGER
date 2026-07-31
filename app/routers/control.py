"""Control Panel API — telnet + goform AppDirect."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..app_settings import load_settings
from ..denon_client import DenonSetupClient
from ..denon_control import (
    SUPPORTED_MODELS,
    ControlBlockedError,
    ControlConfirmRequired,
    DenonControl,
    parse_entities,
    resolve_command_from_id,
)
from ..denon_power import read_main_zone_power
from ..denon_telnet import DenonTelnetError
from ..host_utils import host_label
from ..protocol_loader import CONTROL_LAYOUT_GROUPED, CONTROL_LAYOUTS

router = APIRouter(tags=["control"])


def _default_base(request: Request) -> str:
    return request.app.state.default_host


def _model() -> str:
    m = str(load_settings().get("avr_model") or "AVR-X1200W")
    return m if m in SUPPORTED_MODELS else "AVR-X1200W"


def _layout(override: Optional[str] = None) -> str:
    if override:
        lay = str(override).strip().lower()
        if lay in CONTROL_LAYOUTS:
            return lay
    lay = str(load_settings().get("control_grouping") or CONTROL_LAYOUT_GROUPED).strip().lower()
    return lay if lay in CONTROL_LAYOUTS else CONTROL_LAYOUT_GROUPED


def _control(request: Request) -> DenonControl:
    http = DenonSetupClient(_default_base(request))
    cached: Optional[DenonControl] = getattr(request.app.state, "denon_control", None)
    if cached is not None and cached.http.base == http.base:
        return cached
    ctrl = DenonControl(http)
    request.app.state.denon_control = ctrl
    return ctrl


class CommandBody(BaseModel):
    command: Optional[str] = Field(
        None, description="Raw telnet command, e.g. MUON or MV80"
    )
    id: Optional[str] = Field(
        None, description="Catalog control id (alternative to command)"
    )
    value: Optional[Any] = Field(
        None, description="Value for enum/slider when using id"
    )
    confirm: bool = Field(
        False, description="Required for lock / Quick Memory / reset commands"
    )
    allow_raw: bool = Field(
        False, description="Allow Advanced raw commands outside catalog"
    )
    transport: Optional[str] = Field(
        None, description="Force transport: telnet | goform"
    )
    section: Optional[str] = Field(
        None, description="Section id — return updated entities for this section"
    )
    layout: Optional[str] = Field(
        None, description="grouped | ungrouped — section UI override of Settings"
    )


class QueryBody(BaseModel):
    prefix: str = Field(..., description="Query prefix, e.g. MS or PSTONE CTRL")
    transport: Optional[str] = None


@router.get("/control/catalog")
def control_catalog(
    request: Request,
    layout: Optional[str] = Query(
        None,
        description="Override Settings layout for this request: grouped | ungrouped",
    ),
) -> Dict[str, Any]:
    ctrl = _control(request)
    settings = load_settings()
    data = ctrl.catalog(
        model=_model(),
        show_zone2=bool(settings.get("show_zone2")),
        show_zone3=bool(settings.get("show_zone3")),
        layout=_layout(layout),
    )
    data["host"] = host_label(_default_base(request))
    data["preload"] = getattr(request.app.state, "control_preload", None)
    data["settings_layout"] = _layout()
    return data


@router.get("/control/preload")
def control_preload(request: Request) -> Dict[str, Any]:
    """Startup status preload progress (full status_queries into telnet cache)."""
    state = getattr(request.app.state, "control_preload", None) or {
        "status": "unknown"
    }
    return {"ok": True, **state}


@router.get("/control/status")
def control_status(
    request: Request,
    full: bool = Query(False, description="If true, run full status_queries list"),
    section: Optional[str] = Query(
        None, description="Limit queries/entities to one Control Panel section id"
    ),
    refresh: bool = Query(
        False,
        description=(
            "If true, query the AVR over the shared telnet session. "
            "If false (default), return the in-memory preload/event cache only."
        ),
    ),
    layout: Optional[str] = Query(
        None,
        description="Override Settings layout for this request: grouped | ungrouped",
    ),
) -> Dict[str, Any]:
    ctrl = _control(request)
    power = None
    try:
        power = read_main_zone_power(DenonSetupClient(_default_base(request)))
    except Exception:
        power = None
    lay = _layout(layout)
    try:
        snap = ctrl.status_snapshot(
            full=full,
            section=section,
            power=power,
            refresh=refresh,
            model=_model(),
            layout=lay,
        )
    except Exception as e:
        raise HTTPException(502, f"status failed: {e}") from e
    snap["power"] = power
    snap["host"] = host_label(_default_base(request))
    snap["model"] = _model()
    snap["layout"] = lay
    snap["settings_layout"] = _layout()
    snap["preload"] = getattr(request.app.state, "control_preload", None)
    return snap


@router.post("/control/command")
def control_command(request: Request, body: CommandBody) -> Dict[str, Any]:
    ctrl = _control(request)
    # Prefer explicit layout on the body when the section UI overrode Settings
    layout = _layout(body.layout)
    try:
        if body.id:
            cmd = resolve_command_from_id(body.id, body.value)
        elif body.command:
            cmd = body.command
        else:
            raise HTTPException(400, "Provide command or id")
        result = ctrl.send(
            cmd,
            confirm=body.confirm,
            allow_raw=body.allow_raw,
            force_transport=body.transport,
        )
        # Instant UI update from response + cache (no full re-poll)
        power = None
        try:
            power = read_main_zone_power(DenonSetupClient(_default_base(request)))
        except Exception:
            power = None
        lines = list(result.get("responses") or []) + ctrl.telnet.cached_lines()
        result["entities"] = parse_entities(
            lines, power=power, section_id=body.section, layout=layout
        )
        result["host"] = host_label(_default_base(request))
        result["model"] = _model()
        result["layout"] = layout
        return result
    except ControlConfirmRequired as e:
        raise HTTPException(400, str(e)) from e
    except ControlBlockedError as e:
        raise HTTPException(403, str(e)) from e
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except DenonTelnetError as e:
        raise HTTPException(502, f"telnet error: {e}") from e
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e


@router.post("/control/query")
def control_query(request: Request, body: QueryBody) -> Dict[str, Any]:
    ctrl = _control(request)
    try:
        result = ctrl.query(body.prefix, force_transport=body.transport)
        result["host"] = host_label(_default_base(request))
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except DenonTelnetError as e:
        raise HTTPException(502, f"telnet error: {e}") from e
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
