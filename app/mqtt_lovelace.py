"""Home Assistant Lovelace card YAML — RC-1189 remote layout and generic grids."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml

from .mqtt_ha_naming import build_ha_entity_id_map

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
    """Entity id without domain — for backwards-compatible call sites."""
    from .mqtt_ha_naming import unique_id

    return unique_id(settings, control_id)


def ha_entity_id(settings: Dict[str, Any], control_id: str, component: str) -> str:
    """Deprecated single-entity helper — prefer build_entity_refs."""
    base = str(settings.get("topic") or "denon_avr").replace("/", "_")
    return f"{component}.{base}_{control_id}"


def build_entity_refs(
    settings: Dict[str, Any], catalog_entities: List[Dict[str, Any]]
) -> Dict[str, str]:
    # Use full catalog order for collision suffixes (_2, _3) matching HA discovery.
    id_map = build_ha_entity_id_map(settings, catalog_entities)
    refs: Dict[str, str] = {}
    for ent in catalog_entities:
        if not ent.get("enabled"):
            continue
        cid = str(ent.get("id") or "")
        eid = id_map.get(cid)
        if cid and eid:
            refs[cid] = eid
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



def _service_button(
    entity: Optional[str], name: str, service: str, icon: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    if not entity:
        return None
    card: Dict[str, Any] = {
        "type": "button",
        "name": name,
        "tap_action": {
            "action": "call-service",
            "service": service,
            "target": {"entity_id": entity},
        },
    }
    if icon:
        card["icon"] = icon
    return card


def _rc1189_stack(refs: Dict[str, str], columns: int) -> Dict[str, Any]:
    """Build RC-1189 remote layout (top → bottom like the physical remote)."""
    z2pwr = _pick(refs, "z2_power", "z2_on")
    z2vol = _pick(refs, "z2_vol")
    z2src = _pick(refs, "z2_input")
    eco = _pick(refs, "eco_mode", "eco")
    power = _pick(refs, "pw_power", "pw_on")
    source = _pick(refs, "si_select")
    sleep = _pick(refs, "slp_timer", "slp_set")
    sound = _pick(refs, "ms_select")
    quick = _pick(refs, "ms_quick")
    volume = _pick(refs, "mv_master")
    mute = _pick(refs, "mu_mute", "mu_on")
    up = _pick(refs, "mn_mncup", "ns_ns90")
    down = _pick(refs, "mn_mncdn", "ns_ns91")
    left = _pick(refs, "mn_mnclt", "ns_ns92")
    right = _pick(refs, "mn_mncrt", "ns_ns93")
    enter = _pick(refs, "mn_mnent", "ns_ns94")
    back = _pick(refs, "mn_mnrtn")
    setup = _pick(refs, "mn_menu")
    info = _pick(refs, "mn_mninf")
    option = _pick(refs, "mn_mnopt")
    page_up = _pick(refs, "ns_ns9x")
    page_down = _pick(refs, "ns_ns9y")
    play = _pick(refs, "ns_ns9a")
    pause = _pick(refs, "ns_ns9b")
    skip_minus = _pick(refs, "ns_ns9e")
    skip_plus = _pick(refs, "ns_ns9d")
    tuner_band = _pick(refs, "tm_band")
    tune = _pick(refs, "tf_tune")
    preset = _pick(refs, "tp_preset")

    cards: List[Dict[str, Any]] = [_section_title("Denon RC-1189")]

    z2_row = _compact_cards(
        [
            _tile(z2pwr, "Zone 2", "mdi:home-sound-in"),
            _entity_row(z2vol, "Z2 vol"),
            _select(z2src, "Z2 source"),
        ]
    )
    if z2_row:
        cards.append(
            {"type": "grid", "columns": min(columns, 3), "square": False, "cards": z2_row}
        )

    top = _compact_cards(
        [
            _tile(eco, "ECO", "mdi:leaf"),
            _tile(power, "Power", "mdi:power"),
            _select(source, "Source"),
            _entity_row(sleep, "Sleep"),
        ]
    )
    if top:
        cards.append({"type": "grid", "columns": min(columns, 2), "square": False, "cards": top})

    if sound:
        cards.append(_select(sound, "Sound mode (Movie / Music / Game / Pure)"))

    osd = _compact_cards(
        [
            _service_button(info, "Info", "button.press", "mdi:information-outline"),
            _service_button(option, "Option", "button.press", "mdi:tune-variant"),
            _service_button(back, "Back", "button.press", "mdi:arrow-left"),
            _service_button(setup, "Setup", "button.press", "mdi:cog"),
        ]
    )
    dpad = _compact_cards(
        [
            _service_button(up, "▲", "button.press", "mdi:chevron-up"),
            _service_button(down, "▼", "button.press", "mdi:chevron-down"),
            _service_button(left, "◀", "button.press", "mdi:chevron-left"),
            _service_button(right, "▶", "button.press", "mdi:chevron-right"),
            _service_button(enter, "Enter", "button.press", "mdi:checkbox-blank-circle-outline"),
        ]
    )
    if osd or dpad:
        cards.append(_section_title("Navigation"))
        if osd:
            cards.append(
                {"type": "grid", "columns": min(columns, 4), "square": False, "cards": osd}
            )
        if dpad:
            cards.append(
                {"type": "grid", "columns": min(columns, 3), "square": False, "cards": dpad}
            )

    vol_row = _compact_cards([*_vol_buttons(volume), _tile(mute, "Mute", "mdi:volume-mute")])
    if vol_row:
        cards.append(_section_title("Volume"))
        cards.append({"type": "horizontal-stack", "cards": vol_row})
        if volume:
            cards.append(_entity_row(volume, "Master volume"))

    transport = _compact_cards(
        [
            _service_button(skip_minus, "TUNE −", "button.press", "mdi:skip-previous"),
            _service_button(play, "Play", "button.press", "mdi:play"),
            _service_button(pause, "Pause", "button.press", "mdi:pause"),
            _service_button(skip_plus, "TUNE +", "button.press", "mdi:skip-next"),
        ]
    )
    if transport:
        cards.append(_section_title("Media / Tuner"))
        cards.append(
            {"type": "grid", "columns": min(columns, 4), "square": False, "cards": transport}
        )

    tuner = _compact_cards(
        [
            _select(tuner_band, "Band"),
            _entity_row(tune, "Tune"),
            _entity_row(preset, "Preset / Channel"),
        ]
    )
    if tuner:
        cards.append({"type": "horizontal-stack", "cards": tuner})

    page_row = _compact_cards(
        [
            _service_button(page_up, "Page ▲", "button.press", "mdi:chevron-up"),
            _service_button(page_down, "Page ▼", "button.press", "mdi:chevron-down"),
        ]
    )
    if page_row:
        cards.append({"type": "horizontal-stack", "cards": page_row})

    if quick:
        cards.append(_select(quick, "Quick select 1–4"))

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


def _sections_card(
    refs: Dict[str, str], catalog_entities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Section-grouped tile grids — modern dashboard sections."""
    sections: Dict[str, List[Dict[str, Any]]] = {}
    labels: Dict[str, str] = {}
    for ent in catalog_entities:
        if not ent.get("enabled"):
            continue
        cid = str(ent.get("id") or "")
        entity = refs.get(cid)
        if not entity:
            continue
        sec = str(ent.get("section") or "other")
        labels[sec] = str(ent.get("section_label") or sec)
        sections.setdefault(sec, []).append(
            {"type": "tile", "entity": entity, "name": str(ent.get("label") or cid)}
        )
    cards: List[Dict[str, Any]] = []
    for sec, tiles in sections.items():
        if not tiles:
            continue
        cards.append(
            {
                "type": "grid",
                "title": labels.get(sec, sec),
                "columns": min(4, max(2, len(tiles))),
                "square": False,
                "cards": tiles,
            }
        )
    if not cards:
        cards.append({"type": "markdown", "content": "_No entities enabled._"})
    return {"type": "vertical-stack", "cards": cards}


def _compact_card(refs: Dict[str, str]) -> Dict[str, Any]:
    """Compact top bar: power, mute, volume, source + media row."""
    power = _pick(refs, "pw_power", "pw_on")
    mute = _pick(refs, "mu_mute", "mu_on")
    volume = _pick(refs, "mv_master")
    source = _pick(refs, "si_select")
    sound = _pick(refs, "ms_select")
    play = _pick(refs, "ns_ns9a")
    pause = _pick(refs, "ns_ns9b")
    top = _compact_cards(
        [
            _tile(power, "Power", "mdi:power"),
            _tile(mute, "Mute", "mdi:volume-mute"),
            *_vol_buttons(volume),
            _tile(source, "Source", "mdi:audio-input-rca"),
        ]
    )
    media = _compact_cards(
        [
            _service_button(play, "Play", "button.press", "mdi:play"),
            _service_button(pause, "Pause", "button.press", "mdi:pause"),
            _select(sound, "Sound"),
        ]
    )
    cards: List[Dict[str, Any]] = []
    if top:
        cards.append({"type": "horizontal-stack", "cards": top})
    if volume:
        cards.append(_entity_row(volume, "Volume"))
    if media:
        cards.append({"type": "horizontal-stack", "cards": media})
    return {"type": "vertical-stack", "cards": cards or [{"type": "markdown", "content": "_No entities._"}]}


def _theater_card(refs: Dict[str, str], catalog_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Theater mode — hero controls + section cards below."""
    power = _pick(refs, "pw_power", "pw_on")
    mute = _pick(refs, "mu_mute", "mu_on")
    volume = _pick(refs, "mv_master")
    source = _pick(refs, "si_select")
    hero = _compact_cards(
        [
            _tile(power, "Power", "mdi:power"),
            _tile(mute, "Mute", "mdi:volume-mute"),
            _entity_row(volume, "Volume"),
            _select(source, "Input source"),
        ]
    )
    cards: List[Dict[str, Any]] = [_section_title("Now playing")]
    if hero:
        cards.append({"type": "grid", "columns": 2, "square": False, "cards": hero})
    sections_body = _sections_card(refs, catalog_entities)
    cards.extend(sections_body.get("cards") or [])
    return {"type": "vertical-stack", "cards": cards}


LOVELACE_STYLE_META = {
    "rc1189": {"label": "RC-1189 remote", "path": "denon-rc1189"},
    "grid": {"label": "Entity grid", "path": "denon-grid"},
    "sections": {"label": "Section cards", "path": "denon-sections"},
    "compact": {"label": "Compact bar", "path": "denon-compact"},
    "theater": {"label": "Theater mode", "path": "denon-theater"},
}


def build_lovelace_card(
    settings: Dict[str, Any],
    catalog_entities: List[Dict[str, Any]],
    style: str = "rc1189",
) -> Dict[str, Any]:
    refs = build_entity_refs(settings, catalog_entities)
    device = str(settings.get("device_name") or "Denon AVR")
    meta = LOVELACE_STYLE_META.get(style) or LOVELACE_STYLE_META["rc1189"]
    if style == "grid":
        card = _generic_grid(refs, catalog_entities)
    elif style == "sections":
        card = _sections_card(refs, catalog_entities)
    elif style == "compact":
        card = _compact_card(refs)
    elif style == "theater":
        card = _theater_card(refs, catalog_entities)
    else:
        card = _responsive_remote(refs)
    title = f"{device} — {meta['label']}"

    view = {
        "title": title,
        "path": meta["path"],
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
            "Entity IDs match Home Assistant MQTT discovery (topic slug + control label, "
            "e.g. switch.denon_avr_x1200w_power). Responsive layout uses HA screen conditions."
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
