"""Home Assistant Lovelace card YAML — RC-1189 remote layout and generic grids."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import yaml

from .mqtt_ha_naming import build_publish_entity_id_map

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
    # Match MQTT discovery: enabled controls only (same order as publish).
    id_map = build_publish_entity_id_map(settings, catalog_entities)
    refs: Dict[str, str] = {}
    for ent in catalog_entities:
        if not ent.get("enabled"):
            continue
        cid = str(ent.get("id") or "")
        eid = str(ent.get("ha_entity_id") or id_map.get(cid) or "")
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
        "entity": entity,
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


def _vol_buttons_from_actions(
    volume_set: Optional[str], volume_up: Optional[str], volume_down: Optional[str]
) -> List[Dict[str, Any]]:
    """Rocker order: up then down (physical VOLUME rocker, + on top)."""
    if volume_up and volume_down:
        return _compact_cards(
            [
                _service_button(volume_up, "Vol +", "button.press", "mdi:volume-plus"),
                _service_button(volume_down, "Vol −", "button.press", "mdi:volume-minus"),
            ]
        )
    up_down = _vol_buttons(volume_set)
    if len(up_down) == 2:
        return [up_down[1], up_down[0]]
    return up_down


def _select_option_button(
    entity: Optional[str], name: str, option: str, icon: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    if not entity:
        return None
    card: Dict[str, Any] = {
        "type": "button",
        "name": name,
        "tap_action": {
            "action": "call-service",
            "service": "select.select_option",
            "target": {"entity_id": entity},
            "data": {"option": option},
        },
    }
    if icon:
        card["icon"] = icon
    return card


# RC-1189 face-plate — 4×3 input grid (top → bottom, left → right) per physical remote.
_RC1189_INPUT_GRID: Tuple[Tuple[str, str, str], ...] = (
    ("SAT", "CBL/SAT", "mdi:satellite-variant"),
    ("DVD", "DVD", "mdi:disc"),
    ("BD", "Blu-ray", "mdi:disc-player"),
    ("GAME", "Game", "mdi:gamepad-variant"),
    ("AUX", "AUX1", "mdi:audio-input-rca"),
    ("MPLAY", "Media Player", "mdi:play-network"),
    ("iPod", "USB/iPod", "mdi:ipod"),
    ("TV", "TV Audio", "mdi:television"),
    ("TUNER", "Tuner", "mdi:radio"),
    ("NET", "Online Music", "mdi:music-note"),
    ("BT", "Bluetooth", "mdi:bluetooth"),
    ("iRADIO", "Internet Radio", "mdi:radio-tower"),
)

_RC1189_SOUND_SHORTCUTS: Tuple[Tuple[str, str, str], ...] = (
    ("Movie", "Movie", "mdi:movie-open"),
    ("Music", "Music", "mdi:music"),
    ("Game", "Game", "mdi:gamepad-variant"),
    ("Pure", "Pure Direct", "mdi:headphones"),
)


def _remote_heading(title: str) -> Dict[str, Any]:
    """Section label like the physical RC-1189 face plate."""
    return {
        "type": "markdown",
        "content": f"<center>—— **{title}** ——</center>",
    }


def _section_block(heading: str, card: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not card:
        return []
    return [_remote_heading(heading), card]


def _btn_grid(cards: List[Dict[str, Any]], columns: int, *, square: bool = True) -> Dict[str, Any]:
    return {
        "type": "grid",
        "columns": columns,
        "square": square,
        "cards": cards,
    }


def _vstack(cards: List[Optional[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    compact = _compact_cards(cards)
    if not compact:
        return None
    return {"type": "vertical-stack", "cards": compact}


def _hstack(cards: List[Optional[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    compact = _compact_cards(cards)
    if not compact:
        return None
    return {"type": "horizontal-stack", "cards": compact}


def _entity_icon_btn(
    entity: Optional[str],
    icon: str,
    *,
    name: str = "",
    toggle: bool = False,
) -> Optional[Dict[str, Any]]:
    """Entity-bound icon button — toggle for switches, more-info for selects."""
    if not entity:
        return None
    card: Dict[str, Any] = {
        "type": "button",
        "entity": entity,
        "icon": icon,
        "name": name,
        "show_name": bool(name),
        "show_state": False,
    }
    if toggle:
        card["tap_action"] = {"action": "toggle"}
    return card


def _icon_btn(
    entity: Optional[str],
    icon: str,
    *,
    name: str = "",
    service: str = "button.press",
    option: Optional[str] = None,
    increment: bool = False,
    decrement: bool = False,
    toggle_entity: bool = False,
    cycle: bool = False,
) -> Optional[Dict[str, Any]]:
    if not entity:
        return None
    if toggle_entity:
        return {
            "type": "button",
            "entity": entity,
            "icon": icon,
            "name": name,
            "show_name": bool(name),
            "show_state": False,
            "tap_action": {"action": "toggle"},
        }
    tap: Dict[str, Any] = {"action": "call-service", "target": {"entity_id": entity}}
    if cycle:
        tap["service"] = "select.select_next"
        tap["data"] = {"cycle": True}
    elif option is not None:
        tap["service"] = "select.select_option"
        tap["data"] = {"option": option}
    elif increment:
        tap["service"] = "number.increment"
    elif decrement:
        tap["service"] = "number.decrement"
    else:
        tap["service"] = service
    card: Dict[str, Any] = {
        "type": "button",
        "entity": entity,
        "icon": icon,
        "name": name,
        "show_name": bool(name),
        "tap_action": tap,
    }
    return card


def _press_or_toggle_btn(
    entity: Optional[str],
    icon: str,
    *,
    name: str = "",
) -> Optional[Dict[str, Any]]:
    """Switch → toggle; button → press (matches HA entity domain)."""
    if not entity:
        return None
    if entity.startswith("switch."):
        return _entity_icon_btn(entity, icon, name=name, toggle=True)
    return _icon_btn(entity, icon, name=name)


def _setup_menu_btn(entity: Optional[str]) -> Optional[Dict[str, Any]]:
    """Setup Menu is a select (On/Off) — cycle so a second press closes it."""
    if not entity:
        return None
    if entity.startswith("select."):
        return _icon_btn(entity, "mdi:cog", name="SETUP", cycle=True)
    return _icon_btn(entity, "mdi:cog", name="SETUP")


def _spacer() -> Dict[str, Any]:
    return {"type": "markdown", "content": "&nbsp;"}


def _input_faceplate_grid(
    source_entity: Optional[str],
    ch_up: Optional[str],
    ch_down: Optional[str],
    page_up: Optional[str],
    page_down: Optional[str],
) -> Optional[Dict[str, Any]]:
    """3×4 inputs with CHANNEL / PAGE rail — single 4-column grid (fixes 50/50 split)."""
    if not source_entity:
        return None
    side = [
        _icon_btn(ch_up, "mdi:plus", name="CH+"),
        _icon_btn(ch_down, "mdi:minus", name="CH−"),
        _icon_btn(page_up, "mdi:chevron-up", name="PG▲"),
        _icon_btn(page_down, "mdi:chevron-down", name="PG▼"),
    ]
    cards: List[Optional[Dict[str, Any]]] = []
    for row in range(4):
        for short, option, icon in _RC1189_INPUT_GRID[row * 3 : row * 3 + 3]:
            cards.append(_icon_btn(source_entity, icon, name=short, option=option))
        cards.append(side[row] if row < len(side) else None)
    compact = _compact_cards(cards)
    if not compact:
        return None
    return _btn_grid(compact, 4, square=True)


def _nav_volume_grid(
    *,
    info: Optional[str],
    up: Optional[str],
    option: Optional[str],
    left: Optional[str],
    enter: Optional[str],
    right: Optional[str],
    back: Optional[str],
    down: Optional[str],
    setup: Optional[str],
    vol_btns: List[Dict[str, Any]],
    mute: Optional[str],
) -> Optional[Dict[str, Any]]:
    """3×3 D-pad with volume rocker in a 4th column — single grid."""
    vol_up = vol_btns[0] if len(vol_btns) > 0 else None
    vol_down = vol_btns[1] if len(vol_btns) > 1 else None
    mute_btn = _entity_icon_btn(mute, "mdi:volume-mute", name="MUTE", toggle=True)
    for btn in (vol_up, vol_down, mute_btn):
        if btn:
            btn["show_name"] = False
    cells: List[Optional[Dict[str, Any]]] = [
        _icon_btn(info, "mdi:information-outline", name="INFO"),
        _icon_btn(up, "mdi:chevron-up"),
        _icon_btn(option, "mdi:tune-variant", name="OPT"),
        vol_up,
        _icon_btn(left, "mdi:chevron-left"),
        _icon_btn(enter, "mdi:circle-outline", name="OK"),
        _icon_btn(right, "mdi:chevron-right"),
        vol_down,
        _icon_btn(back, "mdi:arrow-left", name="BACK"),
        _icon_btn(down, "mdi:chevron-down"),
        _setup_menu_btn(setup),
        mute_btn,
    ]
    compact = _compact_cards(cells)
    if not compact:
        return None
    return _btn_grid(compact, 4, square=True)


def _rc1189_compact(refs: Dict[str, str]) -> Dict[str, Any]:
    """Compact RC-1189 layout matching the physical remote (top → bottom)."""
    z2pwr = _pick(refs, "z2_power", "z2_on")
    z2vol = _pick(refs, "z2_vol")
    z2src = _pick(refs, "z2_input")
    source = _pick(refs, "si_select")
    sound = _pick(refs, "ms_select")
    eco = _pick(refs, "eco", "eco_mode")
    power = _pick(refs, "pw_power", "pw_on")
    sleep = _pick(refs, "slp_set", "slp_timer")
    volume = _pick(refs, "mv_set", "mv_master")
    vol_up = _pick(refs, "mv_up")
    vol_down = _pick(refs, "mv_down")
    mute = _pick(refs, "mu_mute", "mu_on")
    up = _pick(refs, "mn_mncup")
    down = _pick(refs, "mn_mncdn")
    left = _pick(refs, "mn_mnclt")
    right = _pick(refs, "mn_mncrt")
    enter = _pick(refs, "mn_mnent")
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
    ch_up = _pick(refs, "tp_up", "tp_preset")
    ch_down = _pick(refs, "tp_down")
    quick1 = _pick(refs, "quick_1")
    quick2 = _pick(refs, "quick_2")
    quick3 = _pick(refs, "quick_3")
    quick4 = _pick(refs, "quick_4")

    cards: List[Dict[str, Any]] = [
        {
            "type": "markdown",
            "content": "<center><strong>RC-1189</strong></center>",
        }
    ]

    # --- ZONE 2 | POWER (side-by-side like physical RC-1189 top) ---
    # Row 1: Z2 ⏻ · Z2 vol ▲ · ECO · PWR
    # Row 2: Z2 SOURCE · Z2 vol ▼ · (spacer) · SLEEP
    top_cells = [
        _press_or_toggle_btn(z2pwr, "mdi:power", name="Z2"),
        _icon_btn(z2vol, "mdi:chevron-up", increment=True),
        _icon_btn(eco, "mdi:leaf", name="ECO", cycle=True)
        if eco and eco.startswith("select.")
        else _entity_icon_btn(eco, "mdi:leaf", name="ECO"),
        _press_or_toggle_btn(power, "mdi:power", name="PWR"),
        _icon_btn(z2src, "mdi:import", name="SOURCE", cycle=True)
        if z2src and z2src.startswith("select.")
        else _entity_icon_btn(z2src, "mdi:import", name="SOURCE"),
        _icon_btn(z2vol, "mdi:chevron-down", decrement=True),
        None,
        _entity_icon_btn(sleep, "mdi:sleep", name="SLEEP"),
    ]
    if any(top_cells):
        filled = [c if c else _spacer() for c in top_cells]
        cards.extend(_section_block("ZONE 2 · POWER", _btn_grid(filled, 4, square=True)))

    # --- INPUT SELECT + CHANNEL / PAGE ---
    input_grid = _input_faceplate_grid(source, ch_up, ch_down, page_up, page_down)
    if input_grid:
        cards.extend(_section_block("INPUT SELECT", input_grid))

    # --- SOUND MODE ---
    sound_btns = _compact_cards(
        [
            _icon_btn(sound, icon, name=label, option=option)
            for label, option, icon in _RC1189_SOUND_SHORTCUTS
        ]
    )
    if sound_btns:
        cards.extend(_section_block("SOUND MODE", _btn_grid(sound_btns, 4, square=True)))

    # --- MENU + VOLUME (single 4×3 grid) ---
    vol_rocker = _vol_buttons_from_actions(volume, vol_up, vol_down)
    nav_vol = _nav_volume_grid(
        info=info,
        up=up,
        option=option,
        left=left,
        enter=enter,
        right=right,
        back=back,
        down=down,
        setup=setup,
        vol_btns=vol_rocker,
        mute=mute,
    )
    if nav_vol:
        cards.extend(_section_block("MENU", nav_vol))

    # --- PLAYBACK ---
    transport = _compact_cards(
        [
            _icon_btn(skip_minus, "mdi:skip-previous", name="TUNE−"),
            _icon_btn(play, "mdi:play"),
            _icon_btn(pause, "mdi:pause"),
            _icon_btn(skip_plus, "mdi:skip-next", name="TUNE+"),
        ]
    )
    if transport:
        cards.extend(_section_block("PLAYBACK", _btn_grid(transport, 4, square=True)))

    # --- QUICK SELECT ---
    quick = _compact_cards(
        [
            _icon_btn(quick1, "mdi:numeric-1-circle-outline", name="1"),
            _icon_btn(quick2, "mdi:numeric-2-circle-outline", name="2"),
            _icon_btn(quick3, "mdi:numeric-3-circle-outline", name="3"),
            _icon_btn(quick4, "mdi:numeric-4-circle-outline", name="4"),
        ]
    )
    if quick:
        cards.extend(_section_block("QUICK SELECT", _btn_grid(quick, 4, square=True)))

    return {"type": "vertical-stack", "cards": cards}


def _rc1189_stack(refs: Dict[str, str], columns: int = 3) -> Dict[str, Any]:
    """Build RC-1189 remote — compact physical layout (columns arg kept for API compat)."""
    del columns
    return _rc1189_compact(refs)


def _responsive_remote(refs: Dict[str, str]) -> Dict[str, Any]:
    """Phone: full width. Tablet/desktop: centered narrow remote column (~33% width)."""
    body = _rc1189_compact(refs)
    narrow = {
        "type": "grid",
        "columns": 5,
        "square": False,
        "cards": [
            {"type": "markdown", "content": " "},
            {"type": "markdown", "content": " "},
            body,
            {"type": "markdown", "content": " "},
            {"type": "markdown", "content": " "},
        ],
    }
    return {
        "type": "vertical-stack",
        "cards": [
            {
                "type": "conditional",
                "conditions": [{"condition": "screen", "media_query": "(max-width: 600px)"}],
                "card": body,
            },
            {
                "type": "conditional",
                "conditions": [{"condition": "screen", "media_query": "(min-width: 601px)"}],
                "card": narrow,
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
    volume = _pick(refs, "mv_set", "mv_master")
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
    volume = _pick(refs, "mv_set", "mv_master")
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
    "rc1189": {
        "label": "RC-1189 remote",
        "path": "denon-rc1189",
        "view_type": "panel",
        "note": (
            "Panel dashboard: phone full-width, desktop centered. "
            "SOURCE under ZONE 2 cycles Zone 2 input. SETUP cycles On/Off. "
            "Skip buttons use skip_next / skip_previous (re-sync MQTT if HA still has skip_2)."
        ),
    },
    "rc1189_card": {
        "label": "RC-1189 card (masonry)",
        "path": "denon-rc1189-card",
        "view_type": "masonry",
        "note": (
            "Masonry / card dashboard — paste as a single view or drop the card into an existing "
            "dashboard. Same physical layout as RC-1189 panel, without the centered desktop wrapper."
        ),
    },
    "grid": {"label": "Entity grid", "path": "denon-grid", "view_type": "panel"},
    "sections": {"label": "Section cards", "path": "denon-sections", "view_type": "panel"},
    "compact": {"label": "Compact bar", "path": "denon-compact", "view_type": "panel"},
    "theater": {"label": "Theater mode", "path": "denon-theater", "view_type": "panel"},
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
    elif style == "rc1189_card":
        card = _rc1189_compact(refs)
    else:
        card = _responsive_remote(refs)
    title = f"{device} — {meta['label']}"
    view_type = str(meta.get("view_type") or "panel")

    view = {
        "title": title,
        "path": meta["path"],
        "type": view_type,
        "cards": [card],
    }
    entities_used = sorted(refs.values())
    yaml_text = yaml.safe_dump(
        {"views": [view]},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    default_note = (
        "Paste into a new dashboard YAML file (Settings → Dashboards → Add dashboard → "
        "New from YAML) or merge the views: entry into an existing lovelace YAML. "
        "RC-1189 style mirrors the physical remote: Zone 2 and Power side by side, "
        "3×4 input grid, D-pad with volume rocker, transport, and quick-select. "
        "Entity IDs match Home Assistant MQTT discovery (topic slug + control label)."
    )
    return {
        "title": title,
        "style": style,
        "entities_used": entities_used,
        "entity_count": len(entities_used),
        "yaml": yaml_text,
        "note": str(meta.get("note") or default_note),
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
