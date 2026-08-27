"""MQTT entity presets — RC-1189 remote map, built-ins, and custom presets."""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Set

from .db import get_setting, upsert_setting
from .protocol_loader import CONTROL_LAYOUT_BOTH, normalize_layout

CUSTOM_PRESETS_KEY = "mqtt_custom_presets"
_PRESET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# Maps control_id → RC-1189 button / region label (UI badges).
RC1189_ENTITY_LABELS: Dict[str, str] = {
    "pw_power": "POWER",
    "pw_on": "POWER On",
    "pw_standby": "POWER Standby",
    "z2_power": "ZONE2 ⏻",
    "z2_on": "ZONE2 On",
    "z2_off": "ZONE2 Off",
    "z2_vol": "ZONE2 Vol ▲▼",
    "z2_input": "ZONE2 SOURCE",
    "z2_mute": "ZONE2 Mute",
    "z2_mu_on": "ZONE2 Mute On",
    "z2_mu_off": "ZONE2 Mute Off",
    "eco_mode": "ECO",
    "eco": "ECO",
    "si_select": "SOURCE + inputs (CBL/SAT…Bluetooth)",
    "slp_timer": "SLEEP",
    "slp_set": "SLEEP timer",
    "slp_off": "SLEEP off",
    "ms_select": "SOUND MODE (Movie/Music/Game/Pure…)",
    "ms_quick": "QUICK SELECT 1–4",
    "mv_master": "VOLUME ▲▼",
    "mu_mute": "MUTE",
    "mu_on": "Mute On",
    "mu_off": "Mute Off",
    "mn_mncup": "Cursor ▲",
    "mn_mncdn": "Cursor ▼",
    "mn_mnclt": "Cursor ◀",
    "mn_mncrt": "Cursor ▶",
    "mn_mnent": "ENTER",
    "mn_mnrtn": "BACK",
    "mn_menu": "SETUP",
    "mn_mninf": "INFO",
    "mn_mnopt": "OPTION",
    "mn_mnchl": "CHANNEL +/−",
    "ns_ns9a": "Play ▶",
    "ns_ns9b": "Pause ⏸",
    "ns_ns9c": "Stop ⏹",
    "ns_ns9d": "Skip + / TUNE +",
    "ns_ns9e": "Skip − / TUNE −",
    "ns_ns90": "Cursor ▲ (media)",
    "ns_ns91": "Cursor ▼ (media)",
    "ns_ns92": "Cursor ◀ (media)",
    "ns_ns93": "Cursor ▶ (media)",
    "ns_ns94": "ENTER (media)",
    "ns_ns9x": "PAGE ▲",
    "ns_ns9y": "PAGE ▼",
    "tm_band": "Tuner AM/FM",
    "tf_tune": "TUNE +/−",
    "tp_preset": "CHANNEL +/−",
    "ps_dyneq": "Dynamic EQ",
    "dimmer": "Display dimmer",
}

RC1189_LESS: List[str] = [
    "z2_power",
    "z2_vol",
    "z2_input",
    "z2_mute",
    "eco_mode",
    "pw_power",
    "si_select",
    "slp_timer",
    "ms_select",
    "ms_quick",
    "mv_master",
    "mu_mute",
    "mn_mncup",
    "mn_mncdn",
    "mn_mnclt",
    "mn_mncrt",
    "mn_mnent",
    "mn_mnrtn",
    "mn_menu",
    "ns_ns9a",
    "ns_ns9b",
    "ns_ns9c",
    "ns_ns9d",
    "ns_ns9e",
    "tm_band",
    "tf_tune",
    "tp_preset",
]

RC1189_MORE: List[str] = [
    "z2_on",
    "z2_off",
    "z2_vol",
    "z2_input",
    "z2_mu_on",
    "z2_mu_off",
    "eco",
    "pw_on",
    "pw_standby",
    "si_select",
    "slp_off",
    "slp_set",
    "ms_select",
    "ms_quick",
    "mv_master",
    "mu_on",
    "mu_off",
    "mn_mncup",
    "mn_mncdn",
    "mn_mnclt",
    "mn_mncrt",
    "mn_mnent",
    "mn_mnrtn",
    "mn_menu",
    "mn_mninf",
    "mn_mnopt",
    "mn_mnchl",
    "ns_ns9a",
    "ns_ns9b",
    "ns_ns9c",
    "ns_ns9d",
    "ns_ns9e",
    "ns_ns90",
    "ns_ns91",
    "ns_ns92",
    "ns_ns93",
    "ns_ns94",
    "ns_ns9x",
    "ns_ns9y",
    "tm_band",
    "tf_tune",
    "tp_preset",
]

RC1189_REMOTE_REGIONS: List[Dict[str, Any]] = [
    {"region": "zone2", "label": "ZONE2 ⏻", "less": ["z2_power"], "more": ["z2_on", "z2_off"]},
    {"region": "zone2_vol", "label": "ZONE2 ▲ (volume)", "less": ["z2_vol"], "more": ["z2_vol"]},
    {"region": "eco", "label": "ECO", "less": ["eco_mode"], "more": ["eco"]},
    {"region": "power", "label": "POWER", "less": ["pw_power"], "more": ["pw_on", "pw_standby"]},
    {"region": "source", "label": "SOURCE", "less": ["si_select"], "more": ["si_select"]},
    {"region": "sleep", "label": "SLEEP", "less": ["slp_timer"], "more": ["slp_off", "slp_set"]},
    {
        "region": "inputs",
        "label": "Input grid (CBL/SAT, DVD, GAME, AUX, Tuner, BT…)",
        "less": ["si_select"],
        "more": ["si_select"],
    },
    {"region": "channel", "label": "CHANNEL +/−", "less": ["tp_preset"], "more": ["tp_preset", "mn_mnchl"]},
    {"region": "page", "label": "PAGE ▲▼", "less": [], "more": ["ns_ns9x", "ns_ns9y"]},
    {
        "region": "sound_shortcuts",
        "label": "MOVIE / MUSIC / GAME / PURE",
        "less": ["ms_select"],
        "more": ["ms_select"],
    },
    {"region": "info", "label": "INFO", "less": [], "more": ["mn_mninf"]},
    {"region": "option", "label": "OPTION", "less": [], "more": ["mn_mnopt"]},
    {"region": "back", "label": "BACK", "less": ["mn_mnrtn"], "more": ["mn_mnrtn"]},
    {"region": "setup", "label": "SETUP", "less": ["mn_menu"], "more": ["mn_menu"]},
    {
        "region": "dpad",
        "label": "D-pad + ENTER",
        "less": ["mn_mncup", "mn_mncdn", "mn_mnclt", "mn_mncrt", "mn_mnent"],
        "more": ["mn_mncup", "mn_mncdn", "mn_mnclt", "mn_mncrt", "mn_mnent"],
    },
    {"region": "volume", "label": "VOLUME ▲▼", "less": ["mv_master"], "more": ["mv_master"]},
    {"region": "mute", "label": "MUTE", "less": ["mu_mute"], "more": ["mu_on", "mu_off"]},
    {
        "region": "transport",
        "label": "|◀ TUNE− / ▶⏸ / TUNE+ ▶|",
        "less": ["ns_ns9e", "ns_ns9a", "ns_ns9b", "ns_ns9d"],
        "more": ["ns_ns9e", "ns_ns9a", "ns_ns9b", "ns_ns9d"],
    },
    {"region": "quick", "label": "QUICK SELECT 1–4", "less": ["ms_quick"], "more": ["ms_quick"]},
    {"region": "z2_source", "label": "ZONE2 SOURCE row", "less": ["z2_input"], "more": ["z2_input"]},
]

BUILTIN_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "ha_essentials",
        "label": "HA essentials",
        "description": "Minimum Home Assistant set: power, volume, mute, source, sound mode, Dynamic EQ.",
        "mode": "featured",
        "remote": None,
        "builtin": True,
        "editable": False,
    },
    {
        "id": "rc1189",
        "label": "RC-1189 (full remote)",
        "description": (
            "Every MQTT entity mapped to the Denon RC-1189 remote: zone 2, power, ECO, sleep, "
            "source inputs, sound shortcuts, D-pad, setup/info/option (more layout), volume, "
            "mute, tuner, media transport, quick select."
        ),
        "remote": "RC-1189",
        "entities": {"less": RC1189_LESS, "more": RC1189_MORE},
        "remote_regions": RC1189_REMOTE_REGIONS,
        "builtin": True,
        "editable": False,
    },
    {
        "id": "rc1189_main",
        "label": "RC-1189 main zone",
        "description": "Main zone only: power, volume, mute, source, sound, quick select, sleep, ECO.",
        "remote": "RC-1189",
        "entities": {
            "less": [
                "pw_power",
                "mv_master",
                "mu_mute",
                "si_select",
                "ms_select",
                "ms_quick",
                "slp_timer",
                "eco_mode",
            ],
            "more": [
                "pw_on",
                "pw_standby",
                "mv_master",
                "mu_on",
                "mu_off",
                "si_select",
                "ms_select",
                "ms_quick",
                "slp_off",
                "slp_set",
                "eco",
            ],
        },
        "builtin": True,
        "editable": False,
    },
    {
        "id": "home_theater",
        "label": "Home theater",
        "description": "All entities in Receiver, Input, Sound Mode, and Timers sections.",
        "sections": ["main", "input", "sound", "timers"],
        "builtin": True,
        "editable": False,
    },
    {
        "id": "all",
        "label": "All entities",
        "description": "Enable every entity in the current control layout.",
        "mode": "all",
        "builtin": True,
        "editable": False,
    },
    {
        "id": "none",
        "label": "Clear all",
        "description": "Disable every entity.",
        "mode": "none",
        "builtin": True,
        "editable": False,
    },
]

# Legacy preset ids from earlier releases.
PRESET_ALIASES: Dict[str, str] = {
    "rc1189_daily": "rc1189_main",
    "rc1189_zone2": "rc1189",
    "rc1189_tuner_media": "rc1189",
}


def load_custom_presets() -> List[Dict[str, Any]]:
    raw = get_setting(CUSTOM_PRESETS_KEY)
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        if not pid or not _PRESET_ID_RE.match(pid):
            continue
        out.append(normalize_custom_preset(item))
    return out


def save_custom_presets(presets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = [normalize_custom_preset(p) for p in presets if isinstance(p, dict)]
    upsert_setting(CUSTOM_PRESETS_KEY, normalized)
    return normalized


def normalize_custom_preset(raw: Dict[str, Any]) -> Dict[str, Any]:
    pid = str(raw.get("id") or "").strip()
    label = str(raw.get("label") or "Custom preset").strip()[:64]
    desc = str(raw.get("description") or "").strip()[:512]
    remote = str(raw.get("remote") or "").strip()[:32] or None
    ent = raw.get("entities")
    entities: Dict[str, List[str]] = {"less": [], "more": []}
    if isinstance(ent, dict):
        for lay in ("less", "more"):
            vals = ent.get(lay)
            if isinstance(vals, list):
                entities[lay] = [str(x) for x in vals if str(x).strip()]
    elif isinstance(ent, list):
        entities["less"] = [str(x) for x in ent if str(x).strip()]
    return {
        "id": pid,
        "label": label or "Custom preset",
        "description": desc,
        "remote": remote,
        "entities": entities,
        "builtin": False,
        "editable": True,
    }


def _resolve_preset_id(preset_id: str) -> str:
    pid = str(preset_id or "").strip()
    return PRESET_ALIASES.get(pid, pid)


def _builtin_by_id() -> Dict[str, Dict[str, Any]]:
    return {p["id"]: p for p in BUILTIN_PRESETS}


def get_preset(preset_id: str) -> Optional[Dict[str, Any]]:
    pid = _resolve_preset_id(preset_id)
    if not pid:
        return None
    built = _builtin_by_id().get(pid)
    if built:
        return dict(built)
    for p in load_custom_presets():
        if p.get("id") == pid:
            return p
    return None


def list_mqtt_presets() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for p in BUILTIN_PRESETS:
        items.append(
            {
                "id": p["id"],
                "label": p["label"],
                "description": p.get("description") or "",
                "remote": p.get("remote"),
                "builtin": True,
                "editable": False,
            }
        )
    for p in load_custom_presets():
        items.append(
            {
                "id": p["id"],
                "label": p["label"],
                "description": p.get("description") or "",
                "remote": p.get("remote"),
                "builtin": False,
                "editable": True,
            }
        )
    return items


def preset_detail(preset_id: str, layout: str) -> Dict[str, Any]:
    preset = get_preset(preset_id)
    if preset is None:
        raise ValueError(f"Unknown MQTT preset: {preset_id}")
    lay = normalize_layout(layout)
    return {
        "id": preset["id"],
        "label": preset.get("label"),
        "description": preset.get("description") or "",
        "remote": preset.get("remote"),
        "builtin": bool(preset.get("builtin")),
        "editable": bool(preset.get("editable")),
        "layout": lay,
        "entity_ids": list((preset.get("entities") or {}).get(lay) or []),
        "remote_regions": preset.get("remote_regions") or [],
        "entity_labels": RC1189_ENTITY_LABELS if preset.get("remote") == "RC-1189" else {},
    }


def _slug_id(label: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40] or "preset"
    return f"custom_{base}_{uuid.uuid4().hex[:6]}"


def create_custom_preset(
    label: str,
    description: str = "",
    entities: Optional[Dict[str, List[str]]] = None,
    remote: Optional[str] = None,
    preset_id: Optional[str] = None,
) -> Dict[str, Any]:
    presets = load_custom_presets()
    pid = str(preset_id or "").strip() or _slug_id(label)
    if not _PRESET_ID_RE.match(pid):
        raise ValueError("Invalid preset id")
    if get_preset(pid) is not None:
        raise ValueError(f"Preset id already exists: {pid}")
    ent = entities if isinstance(entities, dict) else {"less": [], "more": []}
    preset = normalize_custom_preset(
        {
            "id": pid,
            "label": label,
            "description": description,
            "remote": remote,
            "entities": ent,
        }
    )
    presets.append(preset)
    save_custom_presets(presets)
    return preset


def update_custom_preset(preset_id: str, partial: Dict[str, Any]) -> Dict[str, Any]:
    pid = _resolve_preset_id(preset_id)
    preset = get_preset(pid)
    if preset is None:
        raise ValueError(f"Unknown preset: {preset_id}")
    if preset.get("builtin"):
        raise ValueError("Built-in presets cannot be edited — duplicate to custom first")
    presets = load_custom_presets()
    idx = next((i for i, p in enumerate(presets) if p.get("id") == pid), None)
    if idx is None:
        raise ValueError(f"Custom preset not found: {preset_id}")
    merged = {**presets[idx], **partial, "id": pid, "builtin": False, "editable": True}
    presets[idx] = normalize_custom_preset(merged)
    save_custom_presets(presets)
    return presets[idx]


def delete_custom_preset(preset_id: str) -> None:
    pid = _resolve_preset_id(preset_id)
    preset = get_preset(pid)
    if preset is None:
        raise ValueError(f"Unknown preset: {preset_id}")
    if preset.get("builtin"):
        raise ValueError("Built-in presets cannot be deleted")
    presets = [p for p in load_custom_presets() if p.get("id") != pid]
    save_custom_presets(presets)


def _entities_from_enabled_map(enabled: Dict[str, Any]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {"less": [], "more": []}
    for lay in ("less", "more"):
        block = enabled.get(lay)
        if not isinstance(block, dict):
            continue
        out[lay] = sorted(str(k) for k, v in block.items() if v)
    return out


def duplicate_preset(
    preset_id: str,
    label: Optional[str] = None,
    entities: Optional[Dict[str, Any]] = None,
    catalog_entities: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    src = get_preset(preset_id)
    if src is None:
        raise ValueError(f"Unknown preset: {preset_id}")
    new_label = str(label or f"{src.get('label')} (copy)").strip()[:64]
    ent: Dict[str, List[str]]
    if isinstance(entities, dict) and ("less" in entities or "more" in entities):
        ent = _entities_from_enabled_map(entities)
    elif src.get("entities"):
        raw = src.get("entities")
        ent = {
            "less": list((raw or {}).get("less") or []),
            "more": list((raw or {}).get("more") or []),
        }
    elif catalog_entities and src.get("mode"):
        ent = {
            "less": sorted(
                k
                for k, v in build_preset_enabled_map(
                    src["id"], "less", catalog_entities
                ).items()
                if v
            ),
            "more": sorted(
                k
                for k, v in build_preset_enabled_map(
                    src["id"], "more", catalog_entities
                ).items()
                if v
            ),
        }
    else:
        ent = {"less": [], "more": []}
    return create_custom_preset(
        label=new_label,
        description=str(src.get("description") or ""),
        entities=ent,
        remote=src.get("remote"),
    )


def build_preset_enabled_map(
    preset_id: str,
    layout: str,
    catalog_entities: List[Dict[str, Any]],
) -> Dict[str, bool]:
    preset = get_preset(preset_id)
    if preset is None:
        raise ValueError(f"Unknown MQTT preset: {preset_id}")

    lay = normalize_layout(layout)
    all_ids = [str(e.get("id") or "") for e in catalog_entities if e.get("id")]
    mode = preset.get("mode")

    if mode == "all":
        return {cid: True for cid in all_ids}
    if mode == "none":
        return {cid: False for cid in all_ids}
    if mode == "featured":
        featured = {str(e["id"]) for e in catalog_entities if e.get("featured")}
        return {cid: cid in featured for cid in all_ids}

    enabled_ids: Set[str] = set()
    ent_spec = preset.get("entities")
    if isinstance(ent_spec, dict):
        enabled_ids.update(str(x) for x in (ent_spec.get(lay) or ent_spec.get("less") or []))
    elif isinstance(ent_spec, list):
        enabled_ids.update(str(x) for x in ent_spec)

    for sec in preset.get("sections") or []:
        sec_id = str(sec)
        for ent in catalog_entities:
            if str(ent.get("section") or "") == sec_id:
                enabled_ids.add(str(ent.get("id") or ""))

    return {cid: cid in enabled_ids for cid in all_ids}


def apply_mqtt_preset(
    preset_id: str,
    layout: Optional[str],
    catalog_entities: List[Dict[str, Any]],
    current_enabled: Optional[Dict[str, Dict[str, bool]]] = None,
    catalog_entities_more: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, bool]]:
    lay = normalize_layout(layout or "less")
    base: Dict[str, Dict[str, bool]] = {"less": {}, "more": {}}
    if isinstance(current_enabled, dict):
        for key in ("less", "more"):
            ent = current_enabled.get(key)
            if isinstance(ent, dict):
                base[key] = {str(k): bool(v) for k, v in ent.items()}

    if lay == CONTROL_LAYOUT_BOTH:
        base["less"] = build_preset_enabled_map(
            preset_id, "less", catalog_entities
        )
        more_ents = catalog_entities_more if catalog_entities_more is not None else catalog_entities
        base["more"] = build_preset_enabled_map(preset_id, "more", more_ents)
        return base

    other = "more" if lay == "less" else "less"
    base[lay] = build_preset_enabled_map(preset_id, lay, catalog_entities)
    if other not in base:
        base[other] = {}
    return base


def remote_label_for_entity(control_id: str, preset: Optional[Dict[str, Any]] = None) -> Optional[str]:
    if preset and preset.get("remote") == "RC-1189":
        return RC1189_ENTITY_LABELS.get(str(control_id))
    return None


def _normalize_preset_entities(raw: Any) -> Dict[str, Dict[str, bool]]:
    """Accept bool maps or id lists under less/more keys."""
    from .mqtt_settings import _normalize_enabled_entities

    out: Dict[str, Dict[str, bool]] = {"less": {}, "more": {}}
    if isinstance(raw, dict) and ("less" in raw or "more" in raw):
        for lay in ("less", "more"):
            ent = raw.get(lay)
            if isinstance(ent, dict):
                out[lay] = {str(k): bool(v) for k, v in ent.items() if str(k).strip()}
            elif isinstance(ent, list):
                out[lay] = {str(x): True for x in ent if str(x).strip()}
        return out
    return _normalize_enabled_entities(raw)


PRESET_FILE_FORMAT = "denon-avr-manager-mqtt-presets"
PRESET_SNAPSHOT_FORMAT = "denon-avr-manager-mqtt-preset"
PRESET_FILE_VERSION = 1


def export_preset_snapshot(
    *,
    label: str = "Current preset",
    description: str = "",
    remote: Optional[str] = None,
    control_layout: str = "both",
    source_preset_id: Optional[str] = None,
    entities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Export a single preset snapshot (entity selections) for file share — not persisted."""
    from datetime import datetime, timezone

    ent = entities if isinstance(entities, dict) else {"less": {}, "more": {}}
    normalized = _normalize_preset_entities(ent)
    return {
        "format": PRESET_SNAPSHOT_FORMAT,
        "version": PRESET_FILE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "label": str(label or "Current preset").strip()[:64],
        "description": str(description or "").strip()[:512],
        "remote": str(remote or "").strip()[:32] or None,
        "control_layout": normalize_layout(control_layout or "both"),
        "source_preset_id": str(source_preset_id or "").strip() or None,
        "entities": normalized,
    }


def import_preset_snapshot(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate imported preset file and return preview payload.
    Does not write to SQLite — caller applies to UI; user Save persists.
    """
    if not isinstance(raw, dict):
        raise ValueError("Preset file must be a JSON object")
    fmt = str(raw.get("format") or "")
    if fmt == PRESET_FILE_FORMAT:
        raise ValueError(
            "This is a multi-preset library file. Use Export preset for the current selection."
        )
    if fmt and fmt != PRESET_SNAPSHOT_FORMAT:
        raise ValueError(f"Unsupported preset file format: {fmt}")
    entities = _normalize_preset_entities(raw.get("entities"))
    if not any(any(v for v in (entities.get(lay) or {}).values()) for lay in ("less", "more")):
        raise ValueError("Preset file has no entity selections")
    label = str(raw.get("label") or "Imported preset").strip()[:64]
    description = str(raw.get("description") or "").strip()[:512]
    remote = str(raw.get("remote") or "").strip()[:32] or None
    control_layout = normalize_layout(str(raw.get("control_layout") or "both"))
    less_count = sum(1 for v in (entities.get("less") or {}).values() if v)
    more_count = sum(1 for v in (entities.get("more") or {}).values() if v)
    return {
        "label": label,
        "description": description,
        "remote": remote,
        "control_layout": control_layout,
        "source_preset_id": str(raw.get("source_preset_id") or "").strip() or None,
        "enabled_entities": entities,
        "enabled_counts": {"less": less_count, "more": more_count, "total": less_count + more_count},
    }


def export_presets_bundle(include_builtin: bool = False) -> Dict[str, Any]:
    from datetime import datetime, timezone

    custom = load_custom_presets()
    payload: Dict[str, Any] = {
        "format": PRESET_FILE_FORMAT,
        "version": PRESET_FILE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "custom_presets": custom,
    }
    if include_builtin:
        payload["builtin_presets"] = [
            {
                "id": p["id"],
                "label": p.get("label"),
                "description": p.get("description") or "",
                "remote": p.get("remote"),
                "entities": p.get("entities"),
                "sections": p.get("sections"),
                "mode": p.get("mode"),
            }
            for p in BUILTIN_PRESETS
        ]
    return payload


def import_presets_bundle(raw: Dict[str, Any], merge: bool = True) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Preset file must be a JSON object")
    fmt = str(raw.get("format") or "")
    if fmt and fmt != PRESET_FILE_FORMAT:
        raise ValueError(f"Unsupported preset file format: {fmt}")
    incoming = raw.get("custom_presets")
    if not isinstance(incoming, list):
        raise ValueError("Preset file missing custom_presets array")
    existing = load_custom_presets() if merge else []
    by_id = {p["id"]: p for p in existing}
    imported = 0
    for item in incoming:
        if not isinstance(item, dict):
            continue
        preset = normalize_custom_preset(item)
        if preset["id"] in by_id and not merge:
            preset = normalize_custom_preset(
                {**preset, "id": _slug_id(str(preset.get("label") or "imported"))}
            )
        by_id[preset["id"]] = preset
        imported += 1
    merged = save_custom_presets(list(by_id.values()))
    return {"imported": imported, "total_custom": len(merged), "presets": list_mqtt_presets()}
