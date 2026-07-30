"""Persistent app settings (Docker volume JSON — not browser storage)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Defaults used when the file is missing or a key is absent.
DEFAULTS: Dict[str, Any] = {
    "poll_enabled": True,
    "poll_interval_ms": 5000,
    "eq_confirm_ms": 30000,
    "lock_settings_in_standby": True,
    "show_sync_timestamps": True,
    "theme": "system",
    "confirm_network_save": True,
    "confirm_firmware_actions": True,
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
        "key": "poll_interval_ms",
        "label": "Poll interval (ms)",
        "type": "number",
        "min": 2000,
        "max": 120000,
        "step": 500,
        "description": (
            "How often (in milliseconds) the app talks to the AVR while polling is on. "
            "Default 5000 (5 seconds). Lower = fresher UI, more load on the AVR; "
            "higher = quieter network."
        ),
    },
    {
        "key": "eq_confirm_ms",
        "label": "Manual EQ confirm time (ms)",
        "type": "number",
        "min": 0,
        "max": 300000,
        "step": 1000,
        "description": (
            "Before applying a remote Manual EQ curve from the AVR, the same band "
            "values must stay unchanged for this long (default 30000 = 30 seconds). "
            "Prevents the UI from flipping while you are editing. Set 0 to apply "
            "remote EQ changes on the next poll."
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
]


def settings_path() -> Path:
    """Prefer mounted Docker volume `/data`; else local project `data/`."""
    if Path("/data").is_dir():
        return Path("/data/app-settings.json")
    return Path(__file__).resolve().parents[1] / "data" / "app-settings.json"


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

    out["poll_interval_ms"] = _clamp_int(
        src.get("poll_interval_ms", out["poll_interval_ms"]),
        2000,
        120000,
        int(DEFAULTS["poll_interval_ms"]),
    )
    out["eq_confirm_ms"] = _clamp_int(
        src.get("eq_confirm_ms", out["eq_confirm_ms"]),
        0,
        300000,
        int(DEFAULTS["eq_confirm_ms"]),
    )

    theme = str(src.get("theme", out["theme"])).strip().lower()
    out["theme"] = theme if theme in {"system", "light", "dark"} else "system"
    return out


def load_settings() -> Dict[str, Any]:
    path = settings_path()
    if not path.is_file():
        return dict(DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    return normalize_settings(data if isinstance(data, dict) else {})


def _write_settings_file(settings: Dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=".app-settings-",
        suffix=".json",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        Path(tmp_name).replace(path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def ensure_settings_file() -> Dict[str, Any]:
    """Create app-settings.json with defaults on first start if missing."""
    path = settings_path()
    if path.is_file():
        return load_settings()
    settings = dict(DEFAULTS)
    try:
        _write_settings_file(settings)
    except OSError:
        # Volume not writable yet — keep in-memory defaults; UI Save can retry.
        return settings
    return settings


def save_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    """Merge partial updates, write atomically, return normalized settings."""
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


def settings_response() -> Dict[str, Any]:
    path = settings_path()
    return {
        "settings": load_settings(),
        "defaults": dict(DEFAULTS),
        "meta": SETTING_META,
        "path": str(path),
        "exists": path.is_file(),
        "hint": (
            "Stored as /data/app-settings.json on the Docker volume "
            "(survives container restarts). Created automatically on first start. "
            "Not stored in the browser."
        ),
    }
