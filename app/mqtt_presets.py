"""Premade MQTT entity selection presets (RC-1189 remote + HA quick setup)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .protocol_loader import normalize_layout

# RC-1189 is the bundled remote for AVR-X1200W (power, volume, source, sound,
# Quick Select 1–4, sleep, ECO, Zone 2, tuner, media transport).
MQTT_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "ha_essentials",
        "label": "HA essentials",
        "description": (
            "Minimum Home Assistant set: power, volume, mute, source, "
            "sound mode, and Dynamic EQ."
        ),
        "mode": "featured",
        "remote": None,
    },
    {
        "id": "rc1189_daily",
        "label": "RC-1189 daily",
        "description": (
            "Matches the RC-1189 remote for AVR-X1200W: main zone controls, "
            "sound modes, Quick Select, sleep timer, and ECO."
        ),
        "remote": "RC-1189",
        "entities": {
            "less": [
                "pw_power",
                "mv_master",
                "mu_mute",
                "si_select",
                "ms_select",
                "ps_dyneq",
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
                "ps_dyneq",
                "ms_quick",
                "slp_off",
                "slp_set",
                "eco",
            ],
        },
    },
    {
        "id": "rc1189_zone2",
        "label": "RC-1189 + Zone 2",
        "description": (
            "RC-1189 daily controls plus Zone 2 power, volume, mute, and source "
            "(ZONE2 buttons on the remote)."
        ),
        "remote": "RC-1189",
        "entities": {
            "less": [
                "pw_power",
                "mv_master",
                "mu_mute",
                "si_select",
                "ms_select",
                "ps_dyneq",
                "ms_quick",
                "slp_timer",
                "eco_mode",
                "z2_power",
                "z2_vol",
                "z2_mute",
                "z2_input",
            ],
            "more": [
                "pw_on",
                "pw_standby",
                "mv_master",
                "mu_on",
                "mu_off",
                "si_select",
                "ms_select",
                "ps_dyneq",
                "ms_quick",
                "slp_off",
                "slp_set",
                "eco",
                "z2_on",
                "z2_off",
                "z2_vol",
                "z2_mu_on",
                "z2_mu_off",
                "z2_input",
            ],
        },
    },
    {
        "id": "rc1189_tuner_media",
        "label": "RC-1189 tuner & media",
        "description": (
            "Tuner band, tuning, presets, and media transport buttons "
            "(Play/Pause/Skip, cursors, Enter) from the RC-1189."
        ),
        "remote": "RC-1189",
        "entities": {
            "less": [
                "pw_power",
                "mv_master",
                "mu_mute",
                "si_select",
                "tm_band",
                "tf_tune",
                "tp_preset",
                "ns_ns9a",
                "ns_ns9b",
                "ns_ns9c",
                "ns_ns9d",
                "ns_ns9e",
            ],
            "more": [
                "pw_on",
                "pw_standby",
                "mv_master",
                "mu_on",
                "mu_off",
                "si_select",
                "tm_band",
                "tf_tune",
                "tp_preset",
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
            ],
        },
    },
    {
        "id": "home_theater",
        "label": "Home theater",
        "description": (
            "All entities in Receiver, Input, Sound Mode, and Timers sections."
        ),
        "sections": ["main", "input", "sound", "timers"],
    },
    {
        "id": "all",
        "label": "All entities",
        "description": "Enable every entity in the current control layout.",
        "mode": "all",
    },
    {
        "id": "none",
        "label": "Clear all",
        "description": "Disable every entity.",
        "mode": "none",
    },
]

_PRESETS_BY_ID = {p["id"]: p for p in MQTT_PRESETS}


def list_mqtt_presets() -> List[Dict[str, Any]]:
    return [
        {
            "id": p["id"],
            "label": p["label"],
            "description": p.get("description") or "",
            "remote": p.get("remote"),
        }
        for p in MQTT_PRESETS
    ]


def build_preset_enabled_map(
    preset_id: str,
    layout: str,
    catalog_entities: List[Dict[str, Any]],
) -> Dict[str, bool]:
    """Return control_id → enabled for one layout from a preset spec."""
    preset = _PRESETS_BY_ID.get(preset_id)
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
) -> Dict[str, Dict[str, bool]]:
    """Apply preset to one layout; preserve the other layout's selections."""
    lay = normalize_layout(layout or "less")
    other = "more" if lay == "less" else "less"
    base: Dict[str, Dict[str, bool]] = {"less": {}, "more": {}}
    if isinstance(current_enabled, dict):
        for key in ("less", "more"):
            ent = current_enabled.get(key)
            if isinstance(ent, dict):
                base[key] = {str(k): bool(v) for k, v in ent.items()}

    base[lay] = build_preset_enabled_map(preset_id, lay, catalog_entities)
    if other not in base:
        base[other] = {}
    return base
