"""Main Zone power via Denon goform HTTP (no telnet).

Verified on AVR-X1200W:
- Status: GET /goform/formMainZone_MainZoneXmlStatusLite.xml
- Full:   GET /goform/formMainZone_MainZoneXml.xml
- Set:    GET /goform/formiPhoneAppDirect.xml?PWON|PWSTANDBY
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .denon_client import DenonSetupClient

STATUS_LITE = "/goform/formMainZone_MainZoneXmlStatusLite.xml"
STATUS_FULL = "/goform/formMainZone_MainZoneXml.xml"
DIRECT = "/goform/formiPhoneAppDirect.xml"

_TAG_VALUE = re.compile(
    r"<([A-Za-z0-9_]+)>\s*<value>(.*?)</value>\s*</\1>",
    re.I | re.S,
)


def _xml_values(xml: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in _TAG_VALUE.finditer(xml or ""):
        out[m.group(1)] = (m.group(2) or "").strip()
    return out


def _norm_power(raw: str) -> str:
    s = (raw or "").strip().upper()
    if s in {"ON", "1", "POWERON"}:
        return "on"
    if s in {"OFF", "STANDBY", "POWERSTANDBY", "0"}:
        return "standby"
    return "unknown"


def read_main_zone_power(client: DenonSetupClient) -> Dict[str, Any]:
    """Return Main Zone power + display fields from goform XML."""
    values: Dict[str, str] = {}
    try:
        values = _xml_values(client.get(STATUS_FULL))
    except RuntimeError:
        values = {}
    if not values.get("Power"):
        values = _xml_values(client.get(STATUS_LITE))

    power = _norm_power(values.get("Power", ""))
    return {
        "zone": values.get("RenameZone") or "MAIN ZONE",
        "power": power,
        "power_on": power == "on",
        "input": values.get("InputFuncSelect") or "",
        "mute": (values.get("Mute") or "").lower(),
        "volume": values.get("MasterVolume") or "",
        "protocol": "goform",
    }


def set_main_zone_power(
    client: DenonSetupClient, power: str
) -> Dict[str, Any]:
    """Set Main Zone to on or standby via formiPhoneAppDirect.xml."""
    want = (power or "").strip().lower()
    if want in {"on", "pwon", "poweron"}:
        cmd = "PWON"
        want = "on"
    elif want in {"standby", "off", "pwstandby", "powerstandby"}:
        cmd = "PWSTANDBY"
        want = "standby"
    else:
        raise ValueError("power must be 'on' or 'standby'")

    client.get(f"{DIRECT}?{cmd}")
    # Brief settle then re-read (Denon power transitions are not instant).
    import time

    time.sleep(0.8)
    status = read_main_zone_power(client)
    return {
        "requested": want,
        "command": cmd,
        **status,
    }


def toggle_main_zone_power(client: DenonSetupClient) -> Dict[str, Any]:
    status = read_main_zone_power(client)
    nxt = "standby" if status.get("power") == "on" else "on"
    result = set_main_zone_power(client, nxt)
    result["toggled_from"] = status.get("power")
    return result


STANDBY_SETTINGS_BLOCKED = (
    "Main Zone is on Standby. Power On to change settings."
)


def main_zone_is_standby(client: DenonSetupClient) -> bool:
    try:
        return read_main_zone_power(client).get("power") == "standby"
    except RuntimeError:
        return False
