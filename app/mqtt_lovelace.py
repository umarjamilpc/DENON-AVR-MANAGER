"""Home Assistant Lovelace card YAML — RC-1189 remote layout and generic grids."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml

_HA_COMPONENT = {
    "toggle": "switch",
    "enum": "select",
    "slider": "number",
    "stepper": "number",
    "action": "button",
    "query": "button",
    "raw": "text",
}


def ha_object_id(settings: Dict[str, Any], control_id: str) -> str:
    base = str(settings.get("topic") or "denon_avr").replace("/", "_")
    return f"{base}_{control_id}"


def ha_entity_id(settings: Dict[str, Any], control_id: str, component: str) -> str:
    return f"{component}.{ha_object_id(settings, control_id)}"


def build_entity_refs(
    settings: Dict[str, Any], catalog_entities: List[Dict[str, Any]]
) -> Dict[str, str]:
    refs: Dict[str, str] = {}
    for ent in catalog_entities:
        if not ent.get("enabled"):
            continue
        cid = str(ent.get("id") or "")
        if not cid:
            continue
        comp = str(ent.get("ha_component") or _HA_COMPONENT.get(ent.get("kind") or "", "switch"))
        refs[cid] = ha_entity_id(settings, cid, comp)
    return refs


def _pick(refs: Dict[str, str], *control_ids: str) -> Optional[str]:
    for cid in control_ids:
        if cid in refs:
            return refs[cid]
    return None


def _tile(entity: Optional[str], name: str, icon: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not entity:
        return None
    card: Dict[str, Any] = {"type": "tile", "entity": entity, "name": name}
    if icon:
        card["icon"] = icon
    return card


def _entity_row(entity: Optional[str], name: str) -> Optional[Dict[str, Any]]:
    if not entity:
        return None
    return {"type": "entity", "entity": entity, "name": name}


def _select(entity: Optional[str], name: str) -> Optional[Dict[str, Any]]:
    if not entity:
        return None
    return {"type": "entities", "entities": [entity], "title": name, "show_header_toggle": False}


def _vol_buttons(volume_entity: Optional[str]) -> List[Dict[str, Any]]:
    if not volume_entity:
        return []
    return [
        {
            "type": "button",
            "name": "Vol −",
            "icon": "mdi:volume-minus",
            "tap_action": {
                "action": "call-service",
                "service": "number.decrement",
                "target": {"entity_id": volume_entity},
            },
        },
        {
            "type": "button",
            "name": "Vol +",
            "icon": "mdi:volume-plus",
            "tap_action": {
                "action": "call-service",
                "service": "number.increment",
                "target": {"entity_id": volume_entity},
            },
        },
    ]


def _section_title(title: str) -> Dict[str, Any]:
    return {
        "type": "markdown",
        "content": f"**{title}**",
    }


def _compact_cards(cards: List[Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [c for c in cards if c]


def _rc1189_stack(refs: Dict[str, str], columns: int) -> Dict[str, Any]:
    """Build one RC-1189 remote column layout."""
    power = _pick(refs, "pw_power", "pw_on")
    mute = _pick(refs, "mu_mute", "mu_on")
    volume = _pick(refs, "mv_master")
    source = _pick(refs, "si_select")
    sound = _pick(refs, "ms_select")
    quick = _pick(refs, "ms_quick")
    sleep = _pick(refs, "slp_timer", "slp_set")
    eco = _pick(refs, "eco_mode", "eco")
    dyneq = _pick(refs, "ps_dyneq")
    z2pwr = _pick(refs, "z2_power", "z2_on")
    z2vol = _pick(refs, "z2_vol")
    z2mute = _pick(refs, "z2_mute", "z2_mu_on")
    z2src = _pick(refs, "z2_input")
    play = _pick(refs, "ns_ns9a")
    pause = _pick(refs, "ns_ns9b")
    stop = _pick(refs, "ns_ns9c")
    skip_plus = _pick(refs, "ns_ns9d")
    skip_minus = _pick(refs, "ns_ns9e")

    cards: List[Dict[str, Any]] = [
        _section_title("Denon RC-1189"),
    ]

    top = _compact_cards(
        [
            _tile(power, "Power", "mdi:power"),
            _tile(mute, "Mute", "mdi:volume-mute"),
        ]
    )
    if top:
        cards.append({"type": "grid", "columns": min(columns, max(1, len(top))), "square": False, "cards": top})

    vol_row = _compact_cards([*_vol_buttons(volume), _entity_row(volume, "Master volume")])
    if vol_row:
        cards.append({"type": "horizontal-stack", "cards": vol_row})

    for block in (
        _select(source, "Source"),
        _select(sound, "Sound mode"),
        _select(quick, "Quick select"),
        _entity_row(sleep, "Sleep timer"),
        _select(eco, "ECO mode"),
        _tile(dyneq, "Dynamic EQ", "mdi:equalizer"),
    ):
        if block:
            cards.append(block)

    z2_items = _compact_cards(
        [
            _tile(z2pwr, "Zone 2", "mdi:home-sound-in"),
            _tile(z2mute, "Z2 mute", "mdi:volume-mute"),
            _entity_row(z2vol, "Z2 volume"),
            _select(z2src, "Z2 source"),
        ]
    )
    if z2_items:
        cards.append(_section_title("Zone 2"))
        cards.append(
            {
                "type": "grid",
                "columns": min(columns, 2),
                "square": False,
                "cards": z2_items,
            }
        )

    media = _compact_cards(
        [
            _tile(play, "Play", "mdi:play"),
            _tile(pause, "Pause", "mdi:pause"),
            _tile(stop, "Stop", "mdi:stop"),
            _tile(skip_minus, "Skip −", "mdi:skip-previous"),
            _tile(skip_plus, "Skip +", "mdi:skip-next"),
        ]
    )
    if media:
        cards.append(_section_title("Media"))
        cards.append(
            {
                "type": "grid",
                "columns": min(columns, 3),
                "square": False,
                "cards": media,
            }
        )

    return {"type": "vertical-stack", "cards": cards}


def _responsive_remote(refs: Dict[str, str]) -> Dict[str, Any]:
    """Phone / tablet / desktop breakpoints using HA screen conditions."""
    return {
        "type": "vertical-stack",
        "cards": [
            {
                "type": "conditional",
                "conditions": [{"condition": "screen", "media_query": "(max-width: 600px)"}],
                "card": _rc1189_stack(refs, columns=1),
            },
            {
                "type": "conditional",
                "conditions": [
                    {
                        "condition": "screen",
                        "media_query": "(min-width: 601px) and (max-width: 1024px)",
                    }
                ],
                "card": _rc1189_stack(refs, columns=2),
            },
            {
                "type": "conditional",
                "conditions": [{"condition": "screen", "media_query": "(min-width: 1025px)"}],
                "card": {
                    "type": "horizontal-stack",
                    "cards": [
                        {"type": "markdown", "content": "&nbsp;"},
                        {
                            "type": "vertical-stack",
                            "cards": [_rc1189_stack(refs, columns=2)],
                        },
                        {"type": "markdown", "content": "&nbsp;"},
                    ],
                },
            },
        ],
    }


def _generic_grid(refs: Dict[str, str], catalog_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    tiles: List[Dict[str, Any]] = []
    for ent in catalog_entities:
        if not ent.get("enabled"):
            continue
        cid = str(ent.get("id") or "")
        entity = refs.get(cid)
        if not entity:
            continue
        tiles.append({"type": "tile", "entity": entity, "name": str(ent.get("label") or cid)})
    if not tiles:
        tiles.append(
            {
                "type": "markdown",
                "content": "_No MQTT entities enabled — tick entities above and Save._",
            }
        )
    return {
        "type": "grid",
        "columns": 3,
        "square": False,
        "cards": tiles,
    }


def build_lovelace_card(
    settings: Dict[str, Any],
    catalog_entities: List[Dict[str, Any]],
    style: str = "rc1189",
) -> Dict[str, Any]:
    refs = build_entity_refs(settings, catalog_entities)
    device = str(settings.get("device_name") or "Denon AVR")
    if style == "grid":
        card = _generic_grid(refs, catalog_entities)
        title = f"{device} — enabled entities"
    else:
        card = _responsive_remote(refs)
        title = f"{device} — RC-1189 remote"

    view = {
        "title": title,
        "path": "denon-rc1189",
        "type": "panel",
        "cards": [card],
    }
    entities_used = sorted(refs.values())
    yaml_text = yaml.safe_dump(
        {"views": [view]},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    return {
        "title": title,
        "style": style,
        "entities_used": entities_used,
        "entity_count": len(entities_used),
        "yaml": yaml_text,
        "note": (
            "Paste into a new dashboard YAML file (Settings → Dashboards → Add dashboard → "
            "New from YAML) or merge the views: entry into an existing lovelace YAML. "
            "Entity IDs match MQTT discovery object_id ({topic}_{control_id}). "
            "Responsive layout uses HA screen conditions: phone (≤600px), tablet, desktop."
        ),
    }


def catalog_with_enabled_map(
    catalog: Dict[str, Any], enabled_map: Dict[str, bool]
) -> Dict[str, Any]:
    """Return catalog copy with entity enabled flags overridden."""
    out = dict(catalog)
    entities: List[Dict[str, Any]] = []
    sections_map: Dict[str, List[Dict[str, Any]]] = {}
    for ent in catalog.get("entities") or []:
        row = dict(ent)
        cid = str(row.get("id") or "")
        row["enabled"] = bool(enabled_map.get(cid))
        entities.append(row)
        sec = str(row.get("section") or "other")
        sections_map.setdefault(sec, []).append(row)
    out["entities"] = entities
    out["sections_map"] = sections_map
    out["enabled_count"] = sum(1 for e in entities if e.get("enabled"))
    return out
