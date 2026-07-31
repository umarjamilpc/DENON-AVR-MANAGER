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

router = APIRouter(tags=["control"])


def _default_base(request: Request) -> str:
    return request.app.state.default_host


def _model() -> str:
    m = str(load_settings().get("avr_model") or "AVR-X1200W")
    return m if m in SUPPORTED_MODELS else "AVR-X1200W"


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


class QueryBody(BaseModel):
    prefix: str = Field(..., description="Query prefix, e.g. MS or PSTONE CTRL")
    transport: Optional[str] = None


@router.get("/control/catalog")
def control_catalog(request: Request) -> Dict[str, Any]:
    ctrl = _control(request)
    data = ctrl.catalog(model=_model())
    data["host"] = host_label(_default_base(request))
    return data


@router.get("/control/status")
def control_status(
    request: Request,
    full: bool = Query(False, description="If true, run full status_queries list"),
    section: Optional[str] = Query(
        None, description="Limit queries/entities to one Control Panel section id"
    ),
    refresh: bool = Query(
        True,
        description=(
            "If true, query the AVR over the shared telnet session. "
            "If false, return the in-memory event cache only (no AVR traffic)."
        ),
    ),
) -> Dict[str, Any]:
    ctrl = _control(request)
    power = None
    try:
        power = read_main_zone_power(DenonSetupClient(_default_base(request)))
    except Exception:
        power = None
    try:
        snap = ctrl.status_snapshot(
            full=full,
            section=section,
            power=power,
            refresh=refresh,
            model=_model(),
        )
    except Exception as e:
        raise HTTPException(502, f"status failed: {e}") from e
    snap["power"] = power
    snap["host"] = host_label(_default_base(request))
    snap["model"] = _model()
    return snap


@router.post("/control/command")
def control_command(request: Request, body: CommandBody) -> Dict[str, Any]:
    ctrl = _control(request)
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
            lines, power=power, section_id=body.section
        )
        result["host"] = host_label(_default_base(request))
        result["model"] = _model()
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
