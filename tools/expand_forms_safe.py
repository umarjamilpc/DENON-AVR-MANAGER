#!/usr/bin/env python3
"""Safely expand Audio toggle forms (ON), capture fields, then restore prior state.

NEVER touches: firmware update, save/load, setup lock, network IP/DHCP/proxy.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HOST = "http://192.168.20.50"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "protocol" / "expanded_forms"
TIMEOUT = 20

# Only these safe Audio expand/restore targets
TARGETS = [
    {
        "id": "manual_eq",
        "read": f"{HOST}/SETUP/AUDIO/GRAPHICEQ/d_audio.asp",
        "submit": f"{HOST}/SETUP/AUDIO/GRAPHICEQ/s_audio.asp",
        "toggle": "radioGraphicEQ",
        "on": "ON",
        "off": "OFF",
    },
    {
        "id": "dialog_level",
        "read": f"{HOST}/SETUP/AUDIO/DIALOGLEVEL/d_audio.asp",
        "submit": f"{HOST}/SETUP/AUDIO/DIALOGLEVEL/s_audio.asp",
        "toggle": "radioDialogLevelAdjust",
        "on": "ON",
        "off": "OFF",
    },
    {
        "id": "subwoofer_level",
        "read": f"{HOST}/SETUP/AUDIO/SUBWOOFERLEVEL/d_audio.asp",
        "submit": f"{HOST}/SETUP/AUDIO/SUBWOOFERLEVEL/s_audio.asp",
        "toggle": "radioSWLevelAdjustment",
        "on": "ON",
        "off": "OFF",
    },
]


def http(method: str, url: str, data: Optional[Dict[str, str]] = None) -> str:
    body = None
    headers = {"User-Agent": "denon-expand-safe/1.0", "Accept": "text/html,*/*"}
    if data is not None:
        body = urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = Request(url, data=body, headers=headers, method=method)
    with urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def radio_value(html: str, name: str) -> Optional[str]:
    for m in re.finditer(
        rf"<input\b([^>]*name=['\"]{re.escape(name)}['\"][^>]*)>",
        html,
        re.I,
    ):
        attrs = m.group(1)
        if re.search(r"\bchecked\b", attrs, re.I):
            vm = re.search(r"""value\s*=\s*['"]([^'"]*)['"]""", attrs, re.I)
            return vm.group(1) if vm else None
    return None


def field_names(html: str) -> List[str]:
    return sorted(set(re.findall(r"""name=['"]([^'"]+)['"]""", html, re.I)))


def expand_one(t: Dict[str, str]) -> Dict:
    html0 = http("GET", t["read"])
    prior = radio_value(html0, t["toggle"]) or t["off"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{t['id']}_before.html").write_text(html0, encoding="utf-8")

    # Turn ON (temporary)
    http(
        "POST",
        t["submit"],
        {
            "setPureDirectOn": "OFF",
            "setSetupLock": "OFF",
            t["toggle"]: t["on"],
        },
    )
    time.sleep(1.0)
    html_on = http("GET", t["read"])
    (OUT / f"{t['id']}_on.html").write_text(html_on, encoding="utf-8")

    # Restore prior
    http(
        "POST",
        t["submit"],
        {
            "setPureDirectOn": "OFF",
            "setSetupLock": "OFF",
            t["toggle"]: prior,
        },
    )
    time.sleep(1.0)
    html_after = http("GET", t["read"])
    (OUT / f"{t['id']}_after.html").write_text(html_after, encoding="utf-8")
    restored = radio_value(html_after, t["toggle"])

    return {
        "id": t["id"],
        "prior": prior,
        "restored": restored,
        "restore_ok": restored == prior,
        "fields_before": field_names(html0),
        "fields_on": field_names(html_on),
        "fields_after": field_names(html_after),
    }


def main() -> None:
    results = []
    for t in TARGETS:
        print(f"expand {t['id']} ...")
        try:
            results.append(expand_one(t))
        except Exception as exc:  # noqa: BLE001
            results.append({"id": t["id"], "error": str(exc)})
            # best-effort restore to OFF
            try:
                http(
                    "POST",
                    t["submit"],
                    {
                        "setPureDirectOn": "OFF",
                        "setSetupLock": "OFF",
                        t["toggle"]: t["off"],
                    },
                )
            except Exception:
                pass

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "expand_report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
