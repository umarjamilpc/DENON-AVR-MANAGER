"""Home Assistant MQTT entity ID naming — matches HA discovery (label-based, not control_id)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Set

_HA_COMPONENT = {
    "toggle": "switch",
    "enum": "select",
    "slider": "number",
    "stepper": "number",
    "action": "button",
    "query": "button",
    "raw": "text",
}


def slugify(text: str, *, separator: str = "_", max_length: int = 255) -> str:
    """Approximate homeassistant.helpers.text.slugify for entity_id parts."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    cleaned = re.sub(r"[^\w\s-]", "", lowered)
    folded = re.sub(r"[-\s]+", separator, cleaned)
    return folded.strip(separator)[:max_length]


def topic_slug(settings: Dict[str, Any]) -> str:
    raw = str(settings.get("topic") or settings.get("device_name") or "denon_avr")
    return slugify(raw.replace("/", "_"))


def unique_id(settings: Dict[str, Any], control_id: str) -> str:
    """Stable unique_id — topic + control_id (survives label edits in HA registry)."""
    base = str(settings.get("topic") or "denon_avr").replace("/", "_")
    return f"{base}_{control_id}"


def discovery_topic_id(settings: Dict[str, Any], control_id: str) -> str:
    """Discovery topic object_id segment (ASCII slug of unique_id)."""
    return slugify(unique_id(settings, control_id)) or slugify(control_id) or "entity"


def entity_id_slug(settings: Dict[str, Any], label: str) -> str:
    """Entity-id suffix from MQTT discovery name (control label)."""
    base = topic_slug(settings)
    name = slugify(label)
    if base and name:
        return f"{base}_{name}"
    return base or name or "entity"


def default_entity_id(
    settings: Dict[str, Any],
    *,
    component: str,
    label: str,
    used: Set[str],
) -> str:
    """Fully qualified entity_id matching Home Assistant MQTT discovery."""
    stem = entity_id_slug(settings, label)
    candidate = stem
    suffix = 2
    while candidate in used:
        candidate = f"{stem}_{suffix}"
        suffix += 1
    used.add(candidate)
    return f"{component}.{candidate}"


def build_ha_entity_id_map(
    settings: Dict[str, Any],
    controls: Iterable[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Map control_id → fully qualified HA entity_id for a control list.

    Each item needs id, label, and ha_component (or kind).
    Order matches discovery publish order — duplicate labels get _2, _3, …
    """
    used: Set[str] = set()
    out: Dict[str, str] = {}
    for control in controls:
        cid = str(control.get("id") or "")
        if not cid:
            continue
        component = str(
            control.get("ha_component")
            or _HA_COMPONENT.get(str(control.get("kind") or ""), "")
        )
        if not component:
            continue
        label = str(control.get("label") or cid)
        out[cid] = default_entity_id(
            settings, component=component, label=label, used=used
        )
    return out


def ha_entity_id_for_control(
    settings: Dict[str, Any],
    control: Dict[str, Any],
    all_controls: List[Dict[str, Any]],
) -> str:
    """Resolve one control's entity_id using the same collision rules as the full map."""
    return build_ha_entity_id_map(settings, all_controls).get(
        str(control.get("id") or ""), ""
    )
