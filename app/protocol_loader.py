from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from .host_utils import rewrite_endpoint, rewrite_url

PROTOCOL_DIR = Path(__file__).resolve().parents[1] / "protocol"

CONTROL_LAYOUT_GROUPED = "grouped"
CONTROL_LAYOUT_UNGROUPED = "ungrouped"
CONTROL_LAYOUTS = (CONTROL_LAYOUT_GROUPED, CONTROL_LAYOUT_UNGROUPED)


@lru_cache
def load_endpoints() -> List[Dict[str, Any]]:
    return json.loads((PROTOCOL_DIR / "endpoints.json").read_text(encoding="utf-8"))


@lru_cache
def load_catalog() -> List[Dict[str, Any]]:
    path = PROTOCOL_DIR / "catalog.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    from .denon_client import endpoint_id

    out = []
    for e in load_endpoints():
        out.append(
            {
                "id": endpoint_id(e["submit_url"]),
                "section": e["submit_url"].split("/SETUP/")[-1].split("/")[0],
                "title": e["titles"][0] if e.get("titles") else e["submit_url"],
                "submit_url": e["submit_url"],
                "read_urls": e.get("read_urls", []),
                "method": e.get("method", "POST"),
                "field_names": e.get("field_names", []),
            }
        )
    return out


@lru_cache
def load_telnet_protocol(
    layout: str = CONTROL_LAYOUT_GROUPED,
) -> Dict[str, Any]:
    """AVR telnet command catalog for Control Panel (grouped or ungrouped)."""
    layout = (layout or CONTROL_LAYOUT_GROUPED).strip().lower()
    if layout not in CONTROL_LAYOUTS:
        layout = CONTROL_LAYOUT_GROUPED
    path = (
        PROTOCOL_DIR / "telnet_commands.json"
        if layout == CONTROL_LAYOUT_GROUPED
        else PROTOCOL_DIR / "telnet_commands_ungrouped.json"
    )
    if not path.exists():
        # Fall back to the other layout if one file is missing
        alt = PROTOCOL_DIR / "telnet_commands.json"
        if alt.exists():
            path = alt
        else:
            return {
                "model": "AVR-X1200W",
                "sections": [],
                "controls": [],
                "status_queries": [],
                "blocked_commands": [],
                "layout": layout,
            }
    data = json.loads(path.read_text(encoding="utf-8"))
    data["layout"] = layout
    return data


def load_telnet_commands(layout: Optional[str] = None) -> List[Dict[str, Any]]:
    """Controls for one layout, or the union of both (for command allowlists)."""
    if layout is None:
        seen: set[str] = set()
        out: List[Dict[str, Any]] = []
        for lay in CONTROL_LAYOUTS:
            for c in load_telnet_protocol(lay).get("controls") or []:
                cid = str(c.get("id") or "")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                out.append(c)
        return out
    return list(load_telnet_protocol(layout).get("controls") or [])


def get_endpoint(endpoint_id_value: str, base: Optional[str] = None) -> Dict[str, Any]:
    for item in load_catalog():
        if item["id"] == endpoint_id_value:
            full = next(
                e for e in load_endpoints() if e["submit_url"] == item["submit_url"]
            )
            merged = {
                **item,
                "fields": full.get("fields", {}),
                "notes": full.get("notes", []),
            }
            if base:
                return rewrite_endpoint(merged, base)
            return merged
    raise KeyError(endpoint_id_value)


def catalog_for_host(base: str) -> List[Dict[str, Any]]:
    return [rewrite_endpoint(i, base) for i in load_catalog()]


def prefer_read_url(item: Dict[str, Any], base: Optional[str] = None) -> str | None:
    reads = item.get("read_urls") or []
    chosen: Optional[str] = None
    for u in reads:
        name = u.rsplit("/", 1)[-1].lower()
        if name.startswith("d_") and "left" not in name and "right" not in name:
            if "menu" not in u.lower():
                chosen = u
                break
    if chosen is None:
        for u in reads:
            name = u.rsplit("/", 1)[-1].lower()
            if name.startswith("d_"):
                chosen = u
                break
    if chosen is None:
        chosen = reads[0] if reads else None
    if chosen and base:
        return rewrite_url(chosen, base)
    return chosen
