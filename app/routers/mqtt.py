"""MQTT settings and Home Assistant integration API."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from ..app_settings import load_settings
from ..denon_client import DenonSetupClient
from ..denon_control import DenonControl, SUPPORTED_MODELS
from ..host_utils import normalize_host
from ..mqtt_service import get_mqtt_bridge, restart_mqtt_bridge
from ..mqtt_lovelace import build_lovelace_card, catalog_with_enabled_map
from ..mqtt_presets import apply_mqtt_preset, build_preset_enabled_map, list_mqtt_presets
from ..mqtt_settings import (
    enabled_entities_for_layout,
    load_mqtt_settings,
    mqtt_certs_dir,
    mqtt_control_layout,
    normalize_mqtt_settings,
    reset_mqtt_settings,
    save_mqtt_settings,
    settings_response,
)
from ..protocol_loader import normalize_layout

router = APIRouter(tags=["mqtt"])

_HA_COMPONENT_MAP = {
    "toggle": "switch",
    "enum": "select",
    "slider": "number",
    "stepper": "number",
    "action": "button",
    "query": "button",
    "raw": "text",
}

_CERT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class MqttSettingsBody(BaseModel):
    settings: Dict[str, Any] = Field(default_factory=dict)


class MqttPresetBody(BaseModel):
    preset_id: str = Field(..., min_length=1)
    layout: str | None = None


class MqttExportBody(BaseModel):
    layout: str | None = None
    enabled_entities: Dict[str, Any] | None = None
    style: str = "rc1189"
    format: str = "json"


def _control_catalog(layout: str) -> Dict[str, Any]:
    raw_host = os.environ.get("DENON_HOST") or ""
    host = normalize_host(raw_host)
    settings = load_settings()
    model = str(settings.get("avr_model") or "AVR-X1200W")
    if model not in SUPPORTED_MODELS:
        model = "AVR-X1200W"
    lay = normalize_layout(layout)
    ctrl = DenonControl(DenonSetupClient(host))
    return ctrl.catalog(
        model=model,
        show_zone2=bool(settings.get("show_zone2")),
        show_zone3=bool(settings.get("show_zone3")),
        layout=lay,
    )


def _catalog_response(settings: Dict[str, Any], layout: str) -> Dict[str, Any]:
    lay = normalize_layout(layout)
    cat = _control_catalog(lay)
    enabled = enabled_entities_for_layout(settings, lay)
    sections_meta = list(cat.get("sections") or [])
    entities: List[Dict[str, Any]] = []
    sections: Dict[str, List[Dict[str, Any]]] = {}
    section_labels: Dict[str, str] = {
        str(s.get("id")): str(s.get("label") or s.get("id") or "")
        for s in sections_meta
    }

    for c in cat.get("controls") or []:
        kind = c.get("kind")
        if kind not in _HA_COMPONENT_MAP:
            continue
        cid = str(c.get("id") or "")
        sec = str(c.get("section") or "other")
        ent = {
            "id": cid,
            "label": c.get("label"),
            "section": sec,
            "section_label": section_labels.get(sec, sec),
            "kind": kind,
            "ha_component": _HA_COMPONENT_MAP[kind],
            "featured": bool(c.get("featured")),
            "layout": lay,
            "enabled": bool(enabled.get(cid)),
            "command": c.get("command"),
            "query": c.get("query"),
        }
        entities.append(ent)
        sections.setdefault(sec, []).append(ent)

    counts = {}
    totals = {}
    for l in ("less", "more"):
        lay_ent = enabled_entities_for_layout(settings, l)
        cat_l = _control_catalog(l)
        ents = [
            c
            for c in (cat_l.get("controls") or [])
            if c.get("kind") in _HA_COMPONENT_MAP
        ]
        totals[l] = len(ents)
        counts[l] = sum(1 for c in ents if lay_ent.get(str(c.get("id"))))

    return {
        "layout": lay,
        "model": cat.get("model"),
        "sections": sections_meta,
        "entities": entities,
        "sections_map": sections,
        "enabled_count": sum(1 for e in entities if e.get("enabled")),
        "enabled_counts": counts,
        "entity_totals": totals,
    }


@router.get("/mqtt/presets")
def mqtt_list_presets() -> Dict[str, Any]:
    return {"presets": list_mqtt_presets()}


def _preview_preset_response(
    preset_id: str, settings: Dict[str, Any], lay: str
) -> Dict[str, Any]:
    cat = _catalog_response(settings, lay)
    entities = list(cat.get("entities") or [])
    try:
        enabled_map = build_preset_enabled_map(preset_id, lay, entities)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    merged = apply_mqtt_preset(
        preset_id, lay, entities, settings.get("enabled_entities")
    )
    preview_catalog = catalog_with_enabled_map(cat, enabled_map)
    preset = next((p for p in list_mqtt_presets() if p["id"] == preset_id), None)
    return {
        "ok": True,
        "preview": True,
        "preset": preset,
        "layout": lay,
        "enabled_count": preview_catalog.get("enabled_count", 0),
        "enabled_map": enabled_map,
        "enabled_entities": merged,
        "catalog": preview_catalog,
    }


@router.get("/mqtt/presets/{preset_id}/preview")
def mqtt_preview_preset(
    preset_id: str,
    layout: str | None = Query(None, description="less | more"),
) -> Dict[str, Any]:
    settings = load_mqtt_settings()
    lay = normalize_layout(layout or settings.get("control_layout") or "less")
    return _preview_preset_response(preset_id, settings, lay)


@router.post("/mqtt/presets/apply")
def mqtt_apply_preset(body: MqttPresetBody) -> Dict[str, Any]:
    """Load preset into the UI (checkboxes) — does not persist until Save."""
    settings = load_mqtt_settings()
    lay = normalize_layout(body.layout or settings.get("control_layout") or "less")
    return _preview_preset_response(body.preset_id, settings, lay)


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


def _settings_for_export(
    enabled_entities: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    settings = load_mqtt_settings()
    if enabled_entities is not None:
        settings = normalize_mqtt_settings({**settings, "enabled_entities": enabled_entities})
    return settings


@router.get("/mqtt/ha-config")
def mqtt_ha_config(format: str = Query("json", pattern="^(json|yaml)$")) -> Any:
    return _mqtt_ha_config_response(load_mqtt_settings(), format)


@router.post("/mqtt/ha-config")
def mqtt_ha_config_post(body: MqttExportBody) -> Any:
    settings = _settings_for_export(body.enabled_entities)
    fmt = body.format if body.format in {"json", "yaml"} else "json"
    return _mqtt_ha_config_response(settings, fmt)


def _mqtt_ha_config_response(settings: Dict[str, Any], format: str) -> Any:
    bridge = get_mqtt_bridge()
    bridge._settings = settings
    payload = bridge.build_ha_manual_config()
    if format == "yaml":
        return {"yaml": yaml.safe_dump(payload.get("mqtt") or {}, sort_keys=False)}
    return payload


@router.get("/mqtt/lovelace")
def mqtt_lovelace_card(
    style: str = Query("rc1189", pattern="^(rc1189|grid)$"),
    layout: str | None = Query(None, description="less | more"),
) -> Dict[str, Any]:
    settings = load_mqtt_settings()
    lay = normalize_layout(layout or settings.get("control_layout") or "less")
    cat = _catalog_response(settings, lay)
    return build_lovelace_card(
        settings,
        list(cat.get("entities") or []),
        style=style,
    )


@router.post("/mqtt/lovelace")
def mqtt_lovelace_card_post(body: MqttExportBody) -> Dict[str, Any]:
    settings = _settings_for_export(body.enabled_entities)
    lay = normalize_layout(body.layout or settings.get("control_layout") or "less")
    style = body.style if body.style in {"rc1189", "grid"} else "rc1189"
    cat = _catalog_response(settings, lay)
    return build_lovelace_card(
        settings,
        list(cat.get("entities") or []),
        style=style,
    )


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
