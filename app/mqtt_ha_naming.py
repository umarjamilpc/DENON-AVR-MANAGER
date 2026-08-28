"""Home Assistant MQTT entity ID naming — matches HA discovery (label-based, not control_id)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Set

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


def legacy_discovery_object_ids(
    settings: Dict[str, Any],
    control_id: str,
    *,
    extra_topics: Optional[List[str]] = None,
) -> List[str]:
    """Discovery object_id slugs that older builds may have retained on the broker."""
    cid = str(control_id or "").strip()
    if not cid:
        return []
    out: List[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        slug = slugify(raw)
        if slug and slug not in seen:
            seen.add(slug)
            out.append(slug)

    add(cid)
    add(unique_id(settings, cid))
    topic = str(settings.get("topic") or "denon_avr").replace("/", "_")
    add(f"{topic}-{cid}")
    for hist in extra_topics or []:
        tnorm = str(hist or "").replace("/", "_")
        add(f"{tnorm}_{cid}")
        add(f"{tnorm}-{cid}")
    return out


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


# Distinct MQTT discovery names when catalog labels slug to the same entity_id.
# Skip + / Skip − both slug to "skip"; publish order assigns skip then skip_2 (matches HA).
_DISCOVERY_LABEL_OVERRIDES: Dict[str, str] = {
    "ns_ns90": "Network Cursor Up",
    "ns_ns91": "Network Cursor Down",
    "ns_ns92": "Network Cursor Left",
    "ns_ns93": "Network Cursor Right",
}


def discovery_label(control_id: str, label: str) -> str:
    """HA entity_id slug source — override known duplicate labels."""
    return _DISCOVERY_LABEL_OVERRIDES.get(str(control_id or ""), str(label or control_id))


def _control_component(control: Dict[str, Any]) -> str:
    return str(
        control.get("ha_component")
        or _HA_COMPONENT.get(str(control.get("kind") or ""), "")
    )


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
        component = _control_component(control)
        if not component:
            continue
        label = discovery_label(cid, str(control.get("label") or cid))
        out[cid] = default_entity_id(
            settings, component=component, label=label, used=used
        )
    return out


def build_publish_entity_id_map(
    settings: Dict[str, Any],
    catalog_entities: Iterable[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Entity IDs for MQTT discovery / Lovelace — enabled controls only, catalog order.

    Duplicate labels among disabled controls (e.g. network vs menu cursor) must not
    shift IDs for enabled entities.
    """
    publish_controls: List[Dict[str, Any]] = []
    for ent in catalog_entities:
        if not ent.get("enabled"):
            continue
        cid = str(ent.get("id") or "")
        component = _control_component(ent)
        if not cid or not component:
            continue
        publish_controls.append(
            {
                "id": cid,
                "label": discovery_label(cid, str(ent.get("label") or cid)),
                "ha_component": component,
            }
        )
    return build_ha_entity_id_map(settings, publish_controls)


def ha_entity_id_for_control(
    settings: Dict[str, Any],
    control: Dict[str, Any],
    all_controls: List[Dict[str, Any]],
) -> str:
    """Resolve one control's entity_id using the same collision rules as the full map."""
    return build_ha_entity_id_map(settings, all_controls).get(
        str(control.get("id") or ""), ""
    )
