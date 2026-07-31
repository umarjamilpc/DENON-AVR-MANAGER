from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .host_utils import rewrite_endpoint, rewrite_url

PROTOCOL_DIR = Path(__file__).resolve().parents[1] / "protocol"

# Canonical layouts: less = collapse on/off into toggles; more = full discrete
CONTROL_LAYOUT_LESS = "less"
CONTROL_LAYOUT_MORE = "more"
CONTROL_LAYOUTS = (CONTROL_LAYOUT_LESS, CONTROL_LAYOUT_MORE)
# Back-compat aliases used by older settings / clients
CONTROL_LAYOUT_GROUPED = CONTROL_LAYOUT_LESS
CONTROL_LAYOUT_UNGROUPED = CONTROL_LAYOUT_MORE

# On/off action pairs → one toggle (only toggles; enums stay as dropdowns).
# hide: discrete control ids removed in "less" mode
# toggle: control dict inserted (section must match the ungrouped catalog)
_TOGGLE_COLLAPSE: Tuple[Dict[str, Any], ...] = (
    {
        "hide": ("pw_on", "pw_standby"),
        "toggle": {
            "id": "pw_power",
            "section": "power",
            "label": "Power",
            "kind": "toggle",
            "query": "PW?",
            "on_command": "PWON",
            "off_command": "PWSTANDBY",
            "on_label": "On",
            "off_label": "Standby",
            "on_values": ["PWON"],
            "off_values": ["PWSTANDBY"],
            "models": ["X1200W", "X2200W", "X3200W", "X4200W"],
            "x1200w": True,
        },
    },
    {
        "hide": ("zm_on", "zm_off"),
        "toggle": {
            "id": "zm_power",
            "section": "power",
            "label": "Main Zone",
            "kind": "toggle",
            "query": "ZM?",
            "on_command": "ZMON",
            "off_command": "ZMOFF",
            "on_label": "On",
            "off_label": "Off",
            "on_values": ["ZMON"],
            "off_values": ["ZMOFF"],
            "models": ["X1200W", "X2200W", "X3200W", "X4200W"],
            "x1200w": True,
        },
    },
    {
        "hide": ("mu_on", "mu_off"),
        "toggle": {
            "id": "mu_mute",
            "section": "volume",
            "label": "Mute",
            "kind": "toggle",
            "query": "MU?",
            "on_command": "MUON",
            "off_command": "MUOFF",
            "on_label": "Muted",
            "off_label": "Unmuted",
            "on_values": ["MUON"],
            "off_values": ["MUOFF"],
            "models": ["X1200W", "X2200W", "X3200W", "X4200W"],
            "x1200w": True,
        },
    },
    {
        "hide": ("z2_on", "z2_off"),
        "toggle": {
            "id": "z2_power",
            "section": "zone2",
            "label": "ZONE2 Power",
            "kind": "toggle",
            "query": "Z2?",
            "on_command": "Z2ON",
            "off_command": "Z2OFF",
            "on_label": "On",
            "off_label": "Off",
            "on_values": ["Z2ON"],
            "off_values": ["Z2OFF"],
            "models": ["X1200W", "X2200W", "X3200W", "X4200W"],
            "x1200w": True,
        },
    },
    {
        "hide": ("z2_mu_on", "z2_mu_off"),
        "toggle": {
            "id": "z2_mute",
            "section": "zone2",
            "label": "ZONE2 Mute",
            "kind": "toggle",
            "query": "Z2MU?",
            "on_command": "Z2MUON",
            "off_command": "Z2MUOFF",
            "on_label": "Muted",
            "off_label": "Unmuted",
            "on_values": ["Z2MUON"],
            "off_values": ["Z2MUOFF"],
            "models": ["X1200W", "X2200W", "X3200W", "X4200W"],
            "x1200w": True,
        },
    },
)


def normalize_layout(layout: Optional[str]) -> str:
    s = (layout or "").strip().lower().replace("_", " ")
    if s in {
        "more",
        "ungrouped",
        "more controls",
        "full",
    }:
        return CONTROL_LAYOUT_MORE
    if s in {
        "less",
        "grouped",
        "less controls",
        "compact",
    }:
        return CONTROL_LAYOUT_LESS
    return CONTROL_LAYOUT_LESS


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


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_extra_controls(
    base: List[Dict[str, Any]], extras: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Append higher-model-only extras (Zone3 / Auro) not already in the full catalog."""
    seen = {str(c.get("id")) for c in base if c.get("id")}
    out = list(base)
    for c in extras:
        cid = str(c.get("id") or "")
        sec = str(c.get("section") or "")
        if not cid or cid in seen:
            continue
        # Do not import the old streamlined "main"/audio duplicates — only true extras
        if sec == "zone3" or cid == "ms_auro":
            cc = copy.deepcopy(c)
            if cid == "ms_auro":
                cc["section"] = "surround"
            seen.add(cid)
            out.append(cc)
    return out


def _merge_extra_sections(
    base: List[Dict[str, Any]], extras: List[Dict[str, Any]], control_sections: Set[str]
) -> List[Dict[str, Any]]:
    by_id = {str(s.get("id")): s for s in base if s.get("id")}
    for s in extras:
        sid = str(s.get("id") or "")
        # Only allow new sections that actually have controls (e.g. zone3)
        if sid and sid not in by_id and sid in control_sections and sid == "zone3":
            by_id[sid] = s
    ordered: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for s in list(base) + list(extras):
        sid = str(s.get("id") or "")
        if not sid or sid in seen or sid not in control_sections:
            continue
        if sid not in by_id:
            continue
        seen.add(sid)
        ordered.append(by_id[sid])
    return ordered


def _build_more_protocol() -> Dict[str, Any]:
    """Full discrete catalog (+ higher-model extras from the compact file)."""
    full = _load_json(PROTOCOL_DIR / "telnet_commands_ungrouped.json")
    compact = _load_json(PROTOCOL_DIR / "telnet_commands.json")
    controls = _merge_extra_controls(
        list(full.get("controls") or []),
        list(compact.get("controls") or []),
    )
    # Prefer full status query list (larger)
    status = list(full.get("status_queries") or []) or list(
        compact.get("status_queries") or []
    )
    status_lite = list(full.get("status_queries_lite") or []) or list(
        compact.get("status_queries_lite") or []
    )
    section_queries = dict(full.get("section_queries") or {})
    section_queries.update(compact.get("section_queries") or {})
    control_sections = {str(c.get("section")) for c in controls if c.get("section")}
    sections = _merge_extra_sections(
        list(full.get("sections") or []),
        list(compact.get("sections") or []),
        control_sections,
    )
    return {
        "model": full.get("model") or compact.get("model") or "AVR-X1200W",
        "protocol_version": full.get("protocol_version")
        or compact.get("protocol_version"),
        "source": full.get("source") or compact.get("source"),
        "supported_models": full.get("supported_models")
        or compact.get("supported_models"),
        "sections": sections,
        "controls": controls,
        "status_queries": status,
        "status_queries_lite": status_lite,
        "section_queries": section_queries,
        "blocked_commands": list(
            set(full.get("blocked_commands") or [])
            | set(compact.get("blocked_commands") or [])
        ),
        "confirm_prefixes": list(
            dict.fromkeys(
                list(full.get("confirm_prefixes") or [])
                + list(compact.get("confirm_prefixes") or [])
            )
        ),
        "layout": CONTROL_LAYOUT_MORE,
    }


def _build_less_protocol(more: Dict[str, Any]) -> Dict[str, Any]:
    """Same controls as more, but on/off pairs collapsed to toggles only."""
    hide: Set[str] = set()
    inserts: Dict[str, Dict[str, Any]] = {}  # insert before first hidden id
    for rule in _TOGGLE_COLLAPSE:
        for hid in rule["hide"]:
            hide.add(hid)
        tog = copy.deepcopy(rule["toggle"])
        inserts[str(rule["hide"][0])] = tog

    controls: List[Dict[str, Any]] = []
    inserted: Set[str] = set()
    for c in more.get("controls") or []:
        cid = str(c.get("id") or "")
        if cid in inserts and inserts[cid]["id"] not in inserted:
            controls.append(inserts[cid])
            inserted.add(inserts[cid]["id"])
        if cid in hide:
            continue
        # Skip if we already have this toggle id from collapse
        if cid in inserted:
            continue
        controls.append(copy.deepcopy(c))

    # Any toggle whose anchor was missing — append at end of its section
    for rule in _TOGGLE_COLLAPSE:
        tog = rule["toggle"]
        tid = tog["id"]
        if tid in inserted:
            continue
        # place after last control of same section
        idx = max(
            (i for i, x in enumerate(controls) if x.get("section") == tog["section"]),
            default=-1,
        )
        controls.insert(idx + 1, copy.deepcopy(tog))
        inserted.add(tid)

    out = copy.deepcopy(more)
    # Query buttons only in "more controls"
    controls = [c for c in controls if c.get("kind") != "query"]
    out["controls"] = controls
    out["layout"] = CONTROL_LAYOUT_LESS
    return out


@lru_cache
def load_telnet_protocol(
    layout: str = CONTROL_LAYOUT_LESS,
) -> Dict[str, Any]:
    """AVR telnet command catalog for Control Panel (less or more controls)."""
    layout = normalize_layout(layout)
    more = _build_more_protocol()
    if layout == CONTROL_LAYOUT_MORE:
        return more
    return _build_less_protocol(more)


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
    return list(load_telnet_protocol(normalize_layout(layout)).get("controls") or [])


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
