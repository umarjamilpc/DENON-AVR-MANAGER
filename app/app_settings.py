"""Persistent app settings (SQLite on Docker volume — not browser storage)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Defaults used when the file is missing or a key is absent.
DEFAULTS: Dict[str, Any] = {
    "poll_enabled": True,
    "poll_interval_sec": 5,
    "eq_confirm_sec": 30,
    "edit_mode": "realtime",
    "lock_settings_in_standby": True,
    "show_sync_timestamps": True,
    "theme": "system",
    "confirm_network_save": True,
    "confirm_firmware_actions": True,
    "avr_model": "AVR-X1200W",
    # less controls = collapse on/off into toggles; more controls = full discrete
    "control_grouping": "less controls",
    # HA denonavr-style: zones are opt-in (default off to keep Control Panel lean)
    "show_zone2": False,
    "show_zone3": False,
    "telnet_proxy_enabled": True,
    "telnet_proxy_port": 2323,
    "telnet_proxy_baud_rate": 9600,
}

# UI / API schema: label + short explanation for the Settings page.
SETTING_META: List[Dict[str, Any]] = [
    {
        "key": "poll_enabled",
        "label": "Remote polling",
        "type": "boolean",
        "description": (
            "When enabled, the app periodically re-checks Main Zone power and the "
            "open Setup page so changes made on the AVR (or another client) show up "
            "without pressing Reload."
        ),
    },
    {
        "key": "poll_interval_sec",
        "label": "Poll interval (seconds)",
        "type": "number",
        "min": 2,
        "max": 120,
        "step": 1,
        "description": (
            "How often (in seconds) the app talks to the AVR while polling is on. "
            "Default 5. Lower = fresher UI, more load on the AVR; higher = quieter network."
        ),
    },
    {
        "key": "eq_confirm_sec",
        "label": "Manual EQ confirm time (seconds)",
        "type": "number",
        "min": 0,
        "max": 300,
        "step": 1,
        "description": (
            "Before applying a remote Manual EQ curve from the AVR, the same band "
            "values must stay unchanged for this long (default 30 seconds). "
            "Prevents the UI from flipping while you are editing. Set 0 to apply "
            "remote EQ changes on the next poll."
        ),
    },
    {
        "key": "edit_mode",
        "label": "Edit mode",
        "type": "enum",
        "options": ["realtime", "save"],
        "description": (
            "realtime: changes apply to the AVR as you edit (Denon-like). "
            "save: change fields locally, then press Save / Set. "
            "Also available as toggle buttons in the top bar (dev build)."
        ),
    },
    {
        "key": "lock_settings_in_standby",
        "label": "Lock settings in Standby",
        "type": "boolean",
        "description": (
            "When enabled, Setup writes are blocked while Main Zone is on Standby "
            "(Power On still works). Turn off only if you need to change settings "
            "while the zone is in Standby."
        ),
    },
    {
        "key": "show_sync_timestamps",
        "label": "Show sync timestamps",
        "type": "boolean",
        "description": (
            "Show “last checked / last updated” times in the footer and on Manual EQ "
            "so you can see when the UI last talked to the AVR."
        ),
    },
    {
        "key": "theme",
        "label": "Color theme",
        "type": "enum",
        "options": ["system", "light", "dark"],
        "description": (
            "Appearance of this manager UI. “System” follows your OS light/dark preference. "
            "Stored on the server so every browser using this install matches."
        ),
    },
    {
        "key": "confirm_network_save",
        "label": "Confirm Network Save / Connect",
        "type": "boolean",
        "description": (
            "Ask for confirmation before Network Settings Save or Connect. Those "
            "actions can reset the AVR network and drop the session for about a minute."
        ),
    },
    {
        "key": "confirm_firmware_actions",
        "label": "Confirm firmware actions",
        "type": "boolean",
        "description": (
            "Ask for confirmation before Firmware Update, Add New Feature, Web Update, "
            "or local upload. These can reboot the AVR and take a long time."
        ),
    },
    {
        "key": "avr_model",
        "label": "Denon model",
        "type": "enum",
        "options": [
            "AVR-X1200W",
            "AVR-X2200W",
            "AVR-X3200W",
            "AVR-X4200W",
        ],
        "description": (
            "Select your receiver model so the Control Panel only shows commands "
            "supported for that AVR (protocol Ver.02 family). Default AVR-X1200W. "
            "Note: Denon allows only one telnet (TCP port 23) client at a time — "
            "this manager holds that session while it is running."
        ),
    },
    {
        "key": "control_grouping",
        "label": "Control Panel controls",
        "type": "enum",
        "options": ["less controls", "more controls"],
        "description": (
            "less controls: keep the full catalog, but combine On/Off pairs into "
            "one toggle (power, mute, zone power, …). Dropdowns stay as dropdowns; "
            "Query buttons are hidden (use more controls for those). "
            "more controls: show every discrete button including Query, "
            "On/Standby separately, network keys, Quick Select Memory, …)."
        ),
    },
    {
        "key": "show_zone2",
        "label": "Show Zone 2",
        "type": "boolean",
        "description": (
            "When using less controls: show Zone 2 in the nav (like Home Assistant’s "
            "denonavr zone2 option). more controls always includes Zone 2."
        ),
    },
    {
        "key": "show_zone3",
        "label": "Show Zone 3",
        "type": "boolean",
        "description": (
            "When using less controls: show Zone 3 if your model supports it. "
            "more controls includes Zone 3 when the model supports it."
        ),
    },
    {
        "key": "telnet_proxy_enabled",
        "label": "Telnet proxy",
        "type": "boolean",
        "description": (
            "Listen on the proxy port (default 2323) and forward multiple clients "
            "(PuTTY, scripts) through this manager's single AVR telnet session. "
            "Point clients at this host — not the AVR — e.g. telnet nas-ip 2323. "
            "In PuTTY use Connection type Raw or Telnet (not Serial)."
        ),
    },
    {
        "key": "telnet_proxy_port",
        "label": "Telnet proxy port",
        "type": "number",
        "min": 1024,
        "max": 65535,
        "step": 1,
        "description": (
            "TCP port for the telnet proxy (default 2323). Expose this port in "
            "Docker Compose when the proxy is enabled (dev: host 2324 → container 2323)."
        ),
    },
    {
        "key": "telnet_proxy_baud_rate",
        "label": "Telnet proxy baud rate",
        "type": "enum",
        "options": ["9600", "19200", "38400", "57600", "115200"],
        "description": (
            "Reference baud for RS-232 serial adapters (default 9600, matches Denon "
            "documentation). The TCP telnet proxy does not use baud — only PuTTY Serial "
            "mode would. Use Raw/Telnet connection type in PuTTY."
        ),
    },
]


def settings_path() -> Path:
    """Legacy JSON path (migrated into SQLite on first start)."""
    from .db import legacy_settings_json_path

    return legacy_settings_json_path()


def db_file_path() -> Path:
    from .db import db_path

    return db_path()


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def normalize_settings(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge raw dict over defaults and coerce types."""
    src = raw if isinstance(raw, dict) else {}
    out = dict(DEFAULTS)

    if "poll_enabled" in src:
        out["poll_enabled"] = bool(src["poll_enabled"])
    if "lock_settings_in_standby" in src:
        out["lock_settings_in_standby"] = bool(src["lock_settings_in_standby"])
    if "show_sync_timestamps" in src:
        out["show_sync_timestamps"] = bool(src["show_sync_timestamps"])
    if "confirm_network_save" in src:
        out["confirm_network_save"] = bool(src["confirm_network_save"])
    if "confirm_firmware_actions" in src:
        out["confirm_firmware_actions"] = bool(src["confirm_firmware_actions"])
    if "show_zone2" in src:
        out["show_zone2"] = bool(src["show_zone2"])
    if "show_zone3" in src:
        out["show_zone3"] = bool(src["show_zone3"])
    if "telnet_proxy_enabled" in src:
        out["telnet_proxy_enabled"] = bool(src["telnet_proxy_enabled"])

    out["telnet_proxy_port"] = _clamp_int(
        src.get("telnet_proxy_port", out.get("telnet_proxy_port", 2323)),
        1024,
        65535,
        int(DEFAULTS["telnet_proxy_port"]),
    )

    baud_raw = src.get("telnet_proxy_baud_rate", out.get("telnet_proxy_baud_rate", 9600))
    try:
        baud = int(baud_raw)
    except (TypeError, ValueError):
        baud = int(DEFAULTS["telnet_proxy_baud_rate"])
    if baud not in {9600, 19200, 38400, 57600, 115200}:
        baud = int(DEFAULTS["telnet_proxy_baud_rate"])
    out["telnet_proxy_baud_rate"] = baud

    grouping = str(
        src.get("control_grouping", out.get("control_grouping", "less controls"))
    ).strip().lower()
    if grouping in {"grouped", "less", "less controls", "compact"}:
        out["control_grouping"] = "less controls"
    elif grouping in {"ungrouped", "more", "more controls", "full"}:
        out["control_grouping"] = "more controls"
    else:
        out["control_grouping"] = "less controls"

    # Prefer seconds; migrate older poll_interval_ms if present.
    if "poll_interval_sec" in src:
        poll_sec = src.get("poll_interval_sec")
    elif "poll_interval_ms" in src:
        try:
            poll_sec = int(round(int(src["poll_interval_ms"]) / 1000))
        except (TypeError, ValueError):
            poll_sec = DEFAULTS["poll_interval_sec"]
    else:
        poll_sec = out["poll_interval_sec"]
    out["poll_interval_sec"] = _clamp_int(
        poll_sec,
        2,
        120,
        int(DEFAULTS["poll_interval_sec"]),
    )
    if "eq_confirm_sec" in src:
        eq_sec = src.get("eq_confirm_sec")
    elif "eq_confirm_ms" in src:
        try:
            eq_sec = int(round(int(src["eq_confirm_ms"]) / 1000))
        except (TypeError, ValueError):
            eq_sec = DEFAULTS["eq_confirm_sec"]
    else:
        eq_sec = out["eq_confirm_sec"]
    out["eq_confirm_sec"] = _clamp_int(
        eq_sec,
        0,
        300,
        int(DEFAULTS["eq_confirm_sec"]),
    )

    theme = str(src.get("theme", out["theme"])).strip().lower()
    out["theme"] = theme if theme in {"system", "light", "dark"} else "system"

    edit_mode = str(src.get("edit_mode", out.get("edit_mode", "realtime"))).strip().lower()
    out["edit_mode"] = edit_mode if edit_mode in {"realtime", "save"} else "realtime"

    model = str(src.get("avr_model", out.get("avr_model", "AVR-X1200W"))).strip().upper()
    allowed_models = {
        "AVR-X1200W",
        "AVR-X2200W",
        "AVR-X3200W",
        "AVR-X4200W",
    }
    if model in allowed_models:
        out["avr_model"] = model
    elif model.replace("AVR-", "") in {m.replace("AVR-", "") for m in allowed_models}:
        out["avr_model"] = f"AVR-{model.replace('AVR-', '')}"
    else:
        out["avr_model"] = "AVR-X1200W"
    return out


def load_settings() -> Dict[str, Any]:
    from .db import get_setting_rows, init_db

    init_db()
    raw = get_setting_rows()
    return normalize_settings(raw if raw else dict(DEFAULTS))


def _write_settings_file(settings: Dict[str, Any]) -> None:
    from .db import set_setting_rows

    set_setting_rows(settings)


def ensure_settings_file() -> Dict[str, Any]:
    """Initialize SQLite (migrate JSON if present) and ensure defaults exist."""
    from .db import get_setting_rows, init_db, set_setting_rows

    init_db()
    raw = get_setting_rows()
    if not raw:
        settings = dict(DEFAULTS)
        try:
            set_setting_rows(settings)
        except OSError:
            return settings
        return settings
    return normalize_settings(raw)


def save_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    """Merge partial updates, write to SQLite, return normalized settings."""
    current = load_settings()
    if not isinstance(partial, dict):
        raise ValueError("settings must be an object")
    merged = normalize_settings({**current, **partial})
    _write_settings_file(merged)
    return merged


def reset_settings() -> Dict[str, Any]:
    merged = normalize_settings(dict(DEFAULTS))
    _write_settings_file(merged)
    return merged


def build_channel() -> str:
    """production | dev — from APP_BUILD_CHANNEL env (Docker Compose)."""
    raw = str(os.environ.get("APP_BUILD_CHANNEL") or "production").strip().lower()
    return "dev" if raw in {"dev", "development"} else "production"


def settings_response() -> Dict[str, Any]:
    path = db_file_path()
    return {
        "settings": load_settings(),
        "defaults": dict(DEFAULTS),
        "meta": SETTING_META,
        "path": str(path),
        "exists": path.is_file(),
        "build_channel": build_channel(),
        "storage": "sqlite",
        "hint": (
            "Settings and dashboard layout are stored in SQLite on the Docker "
            "volume (/data/app.db) so they survive container reboots."
        ),
    }
