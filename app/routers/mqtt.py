"""MQTT settings and Home Assistant integration API."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from ..app_settings import load_settings
from ..denon_control import filter_controls_for_model
from ..mqtt_service import get_mqtt_bridge, restart_mqtt_bridge
from ..mqtt_settings import (
    enabled_entities_for_layout,
    load_mqtt_settings,
    mqtt_certs_dir,
    mqtt_control_layout,
    reset_mqtt_settings,
    save_mqtt_settings,
    settings_response,
)
from ..protocol_loader import load_telnet_commands, normalize_layout

router = APIRouter(tags=["mqtt"])

_HA_COMPONENT_MAP = {
    "toggle": "switch",
    "enum": "select",
    "slider": "number",
    "stepper": "number",
}

_CERT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class MqttSettingsBody(BaseModel):
    settings: Dict[str, Any] = Field(default_factory=dict)


def _catalog_entities(layout: str) -> List[Dict[str, Any]]:
    model = str(load_settings().get("avr_model") or "AVR-X1200W")
    lay = normalize_layout(layout)
    controls = filter_controls_for_model(load_telnet_commands(lay), model)
    out: List[Dict[str, Any]] = []
    for c in controls:
        kind = c.get("kind")
        if kind not in _HA_COMPONENT_MAP:
            continue
        out.append(
            {
                "id": c.get("id"),
                "label": c.get("label"),
                "section": c.get("section"),
                "kind": kind,
                "ha_component": _HA_COMPONENT_MAP[kind],
                "featured": bool(c.get("featured")),
                "layout": lay,
            }
        )
    return out


def _catalog_response(settings: Dict[str, Any], layout: str) -> Dict[str, Any]:
    lay = normalize_layout(layout)
    enabled = enabled_entities_for_layout(settings, lay)
    entities = _catalog_entities(lay)
    sections: Dict[str, List[Dict[str, Any]]] = {}
    for ent in entities:
        sec = str(ent.get("section") or "other")
        ent["enabled"] = bool(enabled.get(ent["id"]))
        sections.setdefault(sec, []).append(ent)
    counts = {
        l: sum(
            1
            for e in _catalog_entities(l)
            if enabled_entities_for_layout(settings, l).get(e["id"])
        )
        for l in ("less", "more")
    }
    return {
        "layout": lay,
        "entities": entities,
        "sections": sections,
        "enabled_count": sum(1 for e in entities if enabled.get(e["id"])),
        "enabled_counts": counts,
        "entity_totals": {
            l: len(_catalog_entities(l)) for l in ("less", "more")
        },
    }


@router.get("/mqtt/settings")
def mqtt_get_settings() -> Dict[str, Any]:
    data = settings_response()
    data["status"] = get_mqtt_bridge().status()
    data["status"]["control_layout"] = mqtt_control_layout(data["settings"])
    return data


@router.put("/mqtt/settings")
def mqtt_put_settings(body: MqttSettingsBody) -> Dict[str, Any]:
    try:
        saved = save_mqtt_settings(body.settings)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    restart_mqtt_bridge()
    data = settings_response()
    data["settings"] = saved
    data["status"] = get_mqtt_bridge().status()
    data["status"]["control_layout"] = mqtt_control_layout(data["settings"])
    return data


@router.post("/mqtt/settings/reset")
def mqtt_reset_settings() -> Dict[str, Any]:
    saved = reset_mqtt_settings()
    restart_mqtt_bridge()
    data = settings_response()
    data["settings"] = saved
    data["status"] = get_mqtt_bridge().status()
    data["status"]["control_layout"] = mqtt_control_layout(data["settings"])
    return data


@router.get("/mqtt/status")
def mqtt_status() -> Dict[str, Any]:
    return {"ok": True, **get_mqtt_bridge().status()}


@router.post("/mqtt/test")
def mqtt_test_connection() -> Dict[str, Any]:
    restart_mqtt_bridge()
    import time

    time.sleep(1.5)
    status = get_mqtt_bridge().status()
    return {
        "ok": bool(status.get("connected")),
        **status,
    }


@router.get("/mqtt/catalog")
def mqtt_catalog(
    layout: str | None = Query(
        None, description="less | more — defaults to saved control_layout"
    ),
) -> Dict[str, Any]:
    settings = load_mqtt_settings()
    lay = normalize_layout(layout or settings.get("control_layout") or "less")
    return _catalog_response(settings, lay)


@router.get("/mqtt/ha-config")
def mqtt_ha_config(format: str = Query("json", pattern="^(json|yaml)$")) -> Any:
    bridge = get_mqtt_bridge()
    bridge._settings = settings_response()["settings"]
    payload = bridge.build_ha_manual_config()
    if format == "yaml":
        return {"yaml": yaml.safe_dump(payload.get("mqtt") or {}, sort_keys=False)}
    return payload


@router.post("/mqtt/certificate")
async def mqtt_upload_certificate(
    kind: str = Query(..., pattern="^(ca|cert|key)$"),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    original = Path(file.filename or "").name
    if not _CERT_NAME_RE.match(original):
        raise HTTPException(400, "Invalid certificate filename")
    dest = mqtt_certs_dir() / original
    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except OSError as e:
        raise HTTPException(500, f"Failed to save certificate: {e}") from e
    field_map = {"ca": "ca_cert_file", "cert": "client_cert_file", "key": "client_key_file"}
    field = field_map[kind]
    saved = save_mqtt_settings({field: original})
    return {
        "ok": True,
        "kind": kind,
        "filename": original,
        "path": str(dest),
        "settings": saved,
    }
