"""Persistent MQTT bridge settings (SQLite key mqtt_settings)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .mqtt_presets import list_mqtt_presets
from .db import data_dir, get_setting, upsert_setting
from .protocol_loader import normalize_layout, CONTROL_LAYOUT_BOTH, control_source_layout

SETTINGS_KEY = "mqtt_settings"
PUBLISHED_DISCOVERY_KEY = "mqtt_published_discovery"
DISCOVERY_TOPIC_HISTORY_KEY = "mqtt_discovery_topic_history"
_MAX_TOPIC_HISTORY = 8

TLS_MODES = (
    "none",
    "tls_insecure",
    "tls_ca",
    "tls_default",
    "tls_client_cert",
)

DEFAULTS: Dict[str, Any] = {
    "enabled": False,
    "device_name": "Denon AVR",
    "host": "",
    "port": 1883,
    "username": "",
    "password": "",
    "topic": "denon_avr",
    "refresh_sec": 30,
    "discovery_prefix": "homeassistant",
    "json_style": False,
    "ha_discovery": True,
    "tls_mode": "none",
    "ca_cert_file": "",
    "client_cert_file": "",
    "client_key_file": "",
    "control_layout": "both",
    "enabled_entities": {"less": {}, "more": {}},
}

_TOPIC_RE = re.compile(r"^[A-Za-z0-9_./+-]+$")


def mqtt_certs_dir() -> Path:
    path = data_dir() / "mqtt_certs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _norm_topic(value: Any) -> str:
    raw = str(value or "").strip().strip("/")
    if not raw:
        return str(DEFAULTS["topic"])
    if not _TOPIC_RE.match(raw):
        return str(DEFAULTS["topic"])
    return raw


def _normalize_enabled_entities(raw: Any) -> Dict[str, Dict[str, bool]]:
    """Per-layout entity map: less (merged toggles) and more (full discrete)."""
    out: Dict[str, Dict[str, bool]] = {"less": {}, "more": {}}
    if isinstance(raw, dict):
        if "less" in raw or "more" in raw:
            for lay in ("less", "more"):
                ent = raw.get(lay)
                if isinstance(ent, dict):
                    out[lay] = {
                        str(k): bool(v) for k, v in ent.items() if str(k).strip()
                    }
        else:
            # Legacy flat map (pre layout split) → less controls catalog
            out["less"] = {
                str(k): bool(v) for k, v in raw.items() if str(k).strip()
            }
    elif isinstance(raw, list):
        out["less"] = {str(x): True for x in raw if str(x).strip()}
    return out


def mqtt_control_layout(settings: Optional[Dict[str, Any]] = None) -> str:
    src = settings if isinstance(settings, dict) else load_mqtt_settings()
    return normalize_layout(str(src.get("control_layout") or "less"))


def enabled_entities_for_layout(
    settings: Dict[str, Any], layout: Optional[str] = None
) -> Dict[str, bool]:
    lay = normalize_layout(layout or settings.get("control_layout"))
    all_ent = settings.get("enabled_entities") or {}
    if isinstance(all_ent, dict) and lay in all_ent:
        ent = all_ent.get(lay)
        if isinstance(ent, dict):
            return {str(k): bool(v) for k, v in ent.items()}
    return {}


def normalize_mqtt_settings(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}
    out = dict(DEFAULTS)

    if "enabled" in src:
        out["enabled"] = bool(src["enabled"])
    if "json_style" in src:
        out["json_style"] = bool(src["json_style"])
    if "ha_discovery" in src:
        out["ha_discovery"] = bool(src["ha_discovery"])

    out["device_name"] = str(src.get("device_name", out["device_name"]) or "Denon AVR").strip()[
        :64
    ]
    out["host"] = str(src.get("host", out["host"]) or "").strip()[:253]
    out["port"] = _clamp_int(src.get("port", out["port"]), 1, 65535, int(DEFAULTS["port"]))
    out["username"] = str(src.get("username", out["username"]) or "").strip()[:128]
    out["password"] = str(src.get("password", out["password"]) or "").strip()[:256]
    out["topic"] = _norm_topic(src.get("topic", out["topic"]))
    out["refresh_sec"] = _clamp_int(
        src.get("refresh_sec", out["refresh_sec"]), 5, 3600, int(DEFAULTS["refresh_sec"])
    )
    out["discovery_prefix"] = _norm_topic(
        src.get("discovery_prefix", out["discovery_prefix"])
    )

    tls = str(src.get("tls_mode", out["tls_mode"]) or "none").strip().lower()
    out["tls_mode"] = tls if tls in TLS_MODES else "none"

    for key in ("ca_cert_file", "client_cert_file", "client_key_file"):
        out[key] = str(src.get(key, out[key]) or "").strip()

    out["control_layout"] = normalize_layout(
        str(src.get("control_layout", out.get("control_layout", "less")))
    )
    out["enabled_entities"] = _normalize_enabled_entities(src.get("enabled_entities"))

    return out


def load_mqtt_settings() -> Dict[str, Any]:
    raw = get_setting(SETTINGS_KEY)
    return normalize_mqtt_settings(raw if isinstance(raw, dict) else None)


def save_mqtt_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(partial, dict):
        raise ValueError("settings must be an object")
    prior = load_mqtt_settings()
    merged = normalize_mqtt_settings({**prior, **partial})
    upsert_setting(SETTINGS_KEY, merged)
    new_topic = str(merged.get("topic") or "")
    old_topic = str(prior.get("topic") or "")
    if new_topic:
        append_discovery_topic_history(new_topic)
    if old_topic and old_topic != new_topic:
        append_discovery_topic_history(old_topic)
    return merged


def append_discovery_topic_history(topic: str) -> None:
    t = _norm_topic(topic)
    raw = get_setting(DISCOVERY_TOPIC_HISTORY_KEY)
    hist: List[str] = []
    if isinstance(raw, list):
        hist = [str(x).strip() for x in raw if str(x).strip()]
    if t in hist:
        hist.remove(t)
    hist.insert(0, t)
    upsert_setting(DISCOVERY_TOPIC_HISTORY_KEY, hist[:_MAX_TOPIC_HISTORY])


def load_discovery_topic_history() -> List[str]:
    raw = get_setting(DISCOVERY_TOPIC_HISTORY_KEY)
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    seen: set[str] = set()
    for item in raw:
        t = _norm_topic(str(item or ""))
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def reset_mqtt_settings() -> Dict[str, Any]:
    merged = normalize_mqtt_settings(dict(DEFAULTS))
    upsert_setting(SETTINGS_KEY, merged)
    return merged


def cert_path(filename: str) -> Optional[Path]:
    name = str(filename or "").strip()
    if not name or ".." in name or "/" in name or "\\" in name:
        return None
    path = mqtt_certs_dir() / name
    return path if path.is_file() else None


def settings_response() -> Dict[str, Any]:
    settings = load_mqtt_settings()
    return {
        "settings": settings,
        "defaults": dict(DEFAULTS),
        "tls_modes": [
            {"id": "none", "label": "No TLS"},
            {"id": "tls_insecure", "label": "TLS no validation"},
            {"id": "tls_ca", "label": "User TLS (CA certificate)"},
            {"id": "tls_default", "label": "Default TLS (system CA)"},
            {"id": "tls_client_cert", "label": "User client certificates TLS"},
        ],
        "control_layouts": [
            {
                "id": "less",
                "label": "Less controls",
                "description": (
                    "Merged toggles (power, mute, zone power as one switch each). "
                    "Matches Control Panel “less controls” mode."
                ),
            },
            {
                "id": "more",
                "label": "More controls",
                "description": (
                    "Full discrete commands (On/Standby separate, query buttons, …). "
                    "Matches Control Panel “more controls” mode."
                ),
            },
            {
                "id": "both",
                "label": "Both (hybrid)",
                "description": (
                    "Publish less and more entities together — same as the dashboard "
                    "(merged toggles plus discrete/query controls). Each entity uses "
                    "its own less/more enable bucket."
                ),
            },
        ],
        "certs_dir": str(mqtt_certs_dir()),
        "storage": "sqlite",
        "hint": (
            "MQTT settings are stored in SQLite (/data/app.db) and survive reboots. "
            "Upload TLS certificates on this page; filenames are saved in settings."
        ),
        "presets": list_mqtt_presets(),
    }


def entity_enabled(
    settings: Dict[str, Any],
    control_id: str,
    layout: Optional[str] = None,
    source_layout: Optional[str] = None,
) -> bool:
    mode = mqtt_control_layout(settings)
    cid = str(control_id or "")
    if mode == CONTROL_LAYOUT_BOTH:
        bucket = str(source_layout or control_source_layout(cid) or "less")
        enabled = enabled_entities_for_layout(settings, bucket)
    else:
        enabled = enabled_entities_for_layout(settings, layout or mode)
    if not enabled:
        return False
    return bool(enabled.get(cid))


def load_published_discovery() -> List[Dict[str, str]]:
    raw = get_setting(PUBLISHED_DISCOVERY_KEY)
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        dtopic = str(item.get("discovery_topic") or "").strip()
        if not dtopic:
            continue
        out.append(
            {
                "discovery_topic": dtopic,
                "state_topic": str(item.get("state_topic") or "").strip(),
                "control_id": str(item.get("control_id") or "").strip(),
            }
        )
    return out


def save_published_discovery(entries: List[Dict[str, str]]) -> None:
    upsert_setting(PUBLISHED_DISCOVERY_KEY, entries)
