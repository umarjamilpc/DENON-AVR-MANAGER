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
    "poll_interval_sec": 5,
    "eq_confirm_sec": 30,
    "edit_mode": "realtime",
    "lock_settings_in_standby": True,
    "show_sync_timestamps": True,
    "theme": "system",
    "confirm_network_save": True,
    "confirm_firmware_actions": True,
    "avr_model": "AVR-X1200W",
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
    path = settings_path()
    if not path.is_file():
        return dict(DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    raw = data if isinstance(data, dict) else {}
    normalized = normalize_settings(raw)
    # Rewrite once if an older milliseconds key is still on disk.
    legacy = ("poll_interval_ms" in raw and "poll_interval_sec" not in raw) or (
        "eq_confirm_ms" in raw and "eq_confirm_sec" not in raw
    )
    if legacy:
        try:
            _write_settings_file(normalized)
        except OSError:
            pass
    return normalized


def _write_settings_file(settings: Dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Host + container should both be able to edit (entrypoint also chmod a+rwX).
    try:
        os.chmod(path.parent, 0o777)
    except OSError:
        pass
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
        try:
            os.chmod(tmp_name, 0o666)
        except OSError:
            pass
        Path(tmp_name).replace(path)
        try:
            os.chmod(path, 0o666)
        except OSError:
            pass
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


def build_channel() -> str:
    """production | dev — from APP_BUILD_CHANNEL env (Docker Compose)."""
    raw = str(os.environ.get("APP_BUILD_CHANNEL") or "production").strip().lower()
    return "dev" if raw in {"dev", "development"} else "production"


def settings_response() -> Dict[str, Any]:
    path = settings_path()
    return {
        "settings": load_settings(),
        "defaults": dict(DEFAULTS),
        "meta": SETTING_META,
        "path": str(path),
        "exists": path.is_file(),
        "build_channel": build_channel(),
        "hint": (
            "Stored as /data/app-settings.json on the Docker volume "
            "(survives container restarts). Created automatically on first start. "
            "Not stored in the browser."
        ),
    }
