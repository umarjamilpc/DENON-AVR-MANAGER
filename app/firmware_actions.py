"""Firmware Update / Add New Feature / Web Update triggers (Denon SETUP).

Mirrors the X1200W Firmware page JavaScript:
- Update → navigate to s_updatecheck.asp (after setting setUpdateCheck=Start)
- Add New Feature → s_addnewfeature.asp
- Web Update → d_firmwareupdate_push.asp
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .denon_client import DenonSetupClient
from .field_labels import clean_display_text

FIRMWARE_FORM_READ = "/SETUP/GENERAL/FIRMWARE/d_firmware.asp"
FIRMWARE_FORM_SUBMIT = "/SETUP/GENERAL/FIRMWARE/s_firmware.asp"

FIRMWARE_ACTIONS: Dict[str, Dict[str, str]] = {
    "update": {
        "label": "Update",
        "flag": "setUpdateCheck",
        "trigger_path": "/SETUP/GENERAL/FIRMWARE/s_updatecheck.asp",
        "note": "Starts Denon update check (network).",
    },
    "add_new_feature": {
        "label": "Add New Feature",
        "flag": "setAddNewFeature",
        "trigger_path": "/SETUP/GENERAL/FIRMWARE/s_addnewfeature.asp",
        "note": "Starts Add New Feature check on the AVR.",
    },
    "web_update": {
        "label": "Web Update",
        "flag": "setFirmwareUpdateWebUpdate",
        "trigger_path": "/SETUP/GENERAL/FIRMWARE/d_firmwareupdate_push.asp",
        "note": "Opens Denon Web Update page on the AVR.",
    },
}


def _page_snippet(html: str, limit: int = 400) -> str:
    text = clean_display_text(re.sub(r"<script[\s\S]*?</script>", " ", html or "", flags=re.I))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def run_firmware_action(
    client: DenonSetupClient, action: str, *, timeout: Optional[float] = None
) -> Dict[str, Any]:
    """Trigger a firmware page action the way Denon's UI does."""
    meta = FIRMWARE_ACTIONS.get(action)
    if not meta:
        raise ValueError(
            f"Unknown firmware action '{action}'. "
            f"Use one of: {', '.join(FIRMWARE_ACTIONS)}"
        )

    # Preserve current notification radios; set only the action Start flag.
    before = client.read_page(FIRMWARE_FORM_READ)
    fields = before.get("fields") or {}
    payload: Dict[str, str] = {
        "setUpdateCheck": "off",
        "setAddNewFeature": "off",
        "setFirmwareUpdateWebUpdate": "off",
        "setFirmwareUpdate": "off",
        "setPureDirectOn": "OFF",
        "setSetupLock": "OFF",
    }
    for name in ("radioUpdateNotification", "radioUpgradeNotification"):
        meta_f = fields.get(name) or {}
        if isinstance(meta_f, dict) and meta_f.get("value") is not None:
            payload[name] = str(meta_f["value"])

    flag = meta["flag"]
    payload[flag] = "Start"

    # POST Start flag on the firmware form (Denon sets the hidden then navigates).
    try:
        client.post(FIRMWARE_FORM_SUBMIT, payload)
        posted = True
        post_error = None
    except Exception as exc:  # noqa: BLE001
        posted = False
        post_error = str(exc)

    # Navigate to the trigger ASP (as Denon's iframe / top.location does).
    old_timeout = getattr(client, "timeout", 20.0)
    if timeout is not None:
        client.timeout = timeout
    try:
        html = client.get(meta["trigger_path"])
        trigger_ok = True
        trigger_error = None
    except Exception as exc:  # noqa: BLE001
        html = ""
        trigger_ok = False
        trigger_error = str(exc)
    finally:
        client.timeout = old_timeout

    # Refresh main firmware page for after-state
    after = None
    try:
        after = client.read_page(FIRMWARE_FORM_READ)
    except Exception:  # noqa: BLE001
        after = None

    return {
        "action": action,
        "label": meta["label"],
        "trigger_path": meta["trigger_path"],
        "flag": flag,
        "posted_start_flag": posted,
        "post_error": post_error,
        "trigger_ok": trigger_ok,
        "trigger_error": trigger_error,
        "page_snippet": _page_snippet(html) if html else "",
        "note": meta["note"],
        "after": after,
    }
