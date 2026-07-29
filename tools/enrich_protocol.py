#!/usr/bin/env python3
"""Enrich endpoints.json with Manual EQ ON-state fields and build catalog.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROT = ROOT / "protocol"

ATTR = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(['"])(.*?)\2""", re.S)


def attrs(tag_html: str) -> dict:
    out: dict = {}
    for m in ATTR.finditer(tag_html):
        out[m.group(1).lower()] = m.group(3)
    low = tag_html.lower()
    for b in ("checked", "selected", "disabled"):
        if re.search(rf"\b{b}\b", low):
            out[b] = "true"
    return out


def parse_fields(html: str) -> dict:
    fields: dict = {}
    for im in re.finditer(r"<input\b([^>]*)/?>", html, re.I):
        a = attrs(im.group(1))
        name = a.get("name")
        if not name:
            continue
        fields[name] = {
            "tag": "input",
            "name": name,
            "input_type": a.get("type", "text").lower(),
            "value": a.get("value", ""),
            "checked": "checked" in a,
            "disabled": "disabled" in a,
            "min": a.get("min", ""),
            "max": a.get("max", ""),
            "step": a.get("step", ""),
            "options": [],
            "selected": False,
            "extra": {},
        }
    for sm in re.finditer(r"<select\b([^>]*)>(.*?)</select>", html, re.I | re.S):
        a = attrs(sm.group(1))
        name = a.get("name")
        if not name:
            continue
        opts = []
        for om in re.finditer(
            r"<option\b([^>]*)>(.*?)</option>", sm.group(2), re.I | re.S
        ):
            oa = attrs(om.group(1))
            opts.append(
                {
                    "value": oa.get("value", ""),
                    "label": re.sub(r"\s+", " ", om.group(2)).strip(),
                    "selected": "selected" in oa,
                }
            )
        selected = [o["value"] for o in opts if o["selected"]]
        fields[name] = {
            "tag": "select",
            "name": name,
            "input_type": "select",
            "value": selected[0] if selected else "",
            "checked": False,
            "disabled": "disabled" in a,
            "min": "",
            "max": "",
            "step": "",
            "options": opts,
            "selected": bool(selected),
            "extra": {},
        }
    return fields


def main() -> None:
    candidates = [
        PROT / "manual_eq_front_l_on.html",
        ROOT.parent / "denon_x1200w_eq" / "captures" / "manual_eq_front_l_on.html",
    ]
    html = ""
    for c in candidates:
        if c.exists():
            html = c.read_text(encoding="utf-8", errors="replace")
            break
    if not html:
        raise SystemExit("Manual EQ ON capture not found")

    extra = parse_fields(html)
    eps = json.loads((PROT / "endpoints.json").read_text(encoding="utf-8"))
    for e in eps:
        if "GRAPHICEQ/s_audio.asp" in e["submit_url"]:
            e["fields"].update(extra)
            e["field_names"] = sorted(e["fields"].keys())
            e["notes"] = [
                "Enriched with Manual EQ ON-state capture (bands + speaker/channel selects)"
            ]
            print("enriched GEQ field count:", len(e["field_names"]))
            break
    else:
        raise SystemExit("GRAPHICEQ endpoint missing")

    (PROT / "endpoints.json").write_text(json.dumps(eps, indent=2), encoding="utf-8")

    catalog = []
    for e in eps:
        path = e["submit_url"].split("/SETUP/")[-1]
        section = path.split("/")[0]
        catalog.append(
            {
                "id": path.replace("/", "_").replace(".asp", "").lower(),
                "section": section,
                "title": e["titles"][0] if e["titles"] else path,
                "submit_url": e["submit_url"],
                "read_urls": e.get("read_urls", []),
                "method": e["method"],
                "field_names": e["field_names"],
            }
        )
    (PROT / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print("catalog entries:", len(catalog))


if __name__ == "__main__":
    main()
