"""Serialize / parse Dashboard layout as YAML (HA Lovelace–style)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml


def _widget_for_yaml(w: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": w.get("id"),
        "control_id": w.get("control_id"),
        "control_layout": w.get("control_layout") or "less",
        "width_px": int(w.get("width_px") or 0),
        "height_px": int(w.get("height_px") or 0),
        "control_ui": w.get("control_ui") or "auto",
        "shape": w.get("shape") or "square",
        "size": w.get("size") or "md",
        "icon_on": w.get("icon_on") or "",
        "icon_off": w.get("icon_off") or "",
        "color_on": w.get("color_on") or "",
        "color_off": w.get("color_off") or "",
        "custom_name": w.get("custom_name") or "",
    }
    cm = w.get("card_mod")
    if isinstance(cm, dict) and (cm.get("style") or "").strip():
        out["card_mod"] = {"style": str(cm["style"])}
    elif isinstance(cm, str) and cm.strip():
        out["card_mod"] = {"style": cm}
    # Drop empty optional cosmetics
    for key in ("icon_on", "icon_off", "color_on", "color_off", "custom_name"):
        if not out.get(key):
            out.pop(key, None)
    if out.get("control_ui") == "auto":
        # keep for clarity
        pass
    return {k: v for k, v in out.items() if v is not None}


def _section_for_yaml(sec: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": sec.get("id"),
        "title": sec.get("title") or "Section",
        "width_px": int(sec.get("width_px") or 0),
        "height_px": int(sec.get("height_px") or 0),
        "collapsed": bool(sec.get("collapsed")),
        "widgets": [_widget_for_yaml(w) for w in (sec.get("widgets") or []) if isinstance(w, dict)],
    }
    cm = sec.get("card_mod")
    if isinstance(cm, dict) and (cm.get("style") or "").strip():
        out["card_mod"] = {"style": str(cm["style"])}
    return out


def dashboard_to_yaml(data: Dict[str, Any]) -> str:
    """Export layouts (preferred) or flat sections to YAML text."""
    layouts = data.get("layouts") or []
    doc: Dict[str, Any] = {
        "title": "Dashboard",
        "layouts": [],
    }
    if layouts:
        for ly in layouts:
            if not isinstance(ly, dict):
                continue
            doc["layouts"].append(
                {
                    "id": ly.get("id"),
                    "stack": ly.get("stack") or "horizontal",
                    "sections": [
                        _section_for_yaml(s)
                        for s in (ly.get("sections") or [])
                        if isinstance(s, dict)
                    ],
                }
            )
    else:
        doc["layouts"] = [
            {
                "id": None,
                "stack": "horizontal",
                "sections": [
                    _section_for_yaml(s)
                    for s in (data.get("sections") or [])
                    if isinstance(s, dict)
                ],
            }
        ]
    return yaml.safe_dump(
        doc,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )


def _parse_card_mod(raw: Any) -> Optional[Dict[str, str]]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, str):
        s = raw.strip()
        return {"style": s} if s else None
    if isinstance(raw, dict):
        style = raw.get("style")
        if isinstance(style, dict):
            # card-mod dict form: { ".dash-card": "color: red" }
            parts = []
            for sel, body in style.items():
                parts.append(f"{sel} {{\n{body}\n}}")
            style = "\n".join(parts)
        style_s = str(style or "").strip()
        return {"style": style_s} if style_s else None
    return None


def yaml_to_dashboard(text: str) -> Dict[str, Any]:
    """Parse YAML into replace_dashboard payload {layouts, sections}."""
    try:
        doc = yaml.safe_load(text) if text and text.strip() else {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}") from e
    if doc is None:
        doc = {}
    if not isinstance(doc, dict):
        raise ValueError("YAML root must be a mapping (object)")

    layouts_in = doc.get("layouts")
    sections_flat: List[Dict[str, Any]] = []

    def _sort_order(raw: Any, default: int) -> int:
        if raw is None:
            return default
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    def norm_widget(w: Any, index: int = 0) -> Optional[Dict[str, Any]]:
        if not isinstance(w, dict):
            return None
        cid = str(w.get("control_id") or "").strip()
        if not cid:
            return None
        out = {
            "id": w.get("id"),
            "control_id": cid,
            "control_layout": w.get("control_layout") or "less",
            "sort_order": _sort_order(w.get("sort_order"), index),
            "shape": w.get("shape") or "square",
            "size": w.get("size") or "md",
            "width_px": w.get("width_px") or 0,
            "height_px": w.get("height_px") or 0,
            "control_ui": w.get("control_ui") or "auto",
            "icon_on": w.get("icon_on") or "",
            "icon_off": w.get("icon_off") or "",
            "color_on": w.get("color_on") or "",
            "color_off": w.get("color_off") or "",
            "custom_name": str(w.get("custom_name") or "").strip(),
            "card_mod": _parse_card_mod(w.get("card_mod")),
        }
        return out

    def norm_section(
        sec: Any, layout_id: str = "", index: int = 0
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(sec, dict):
            return None
        widgets = []
        for wi, w in enumerate(sec.get("widgets") or []):
            nw = norm_widget(w, wi)
            if nw:
                widgets.append(nw)
        return {
            "id": sec.get("id"),
            "title": sec.get("title") or "Section",
            "collapsed": bool(sec.get("collapsed")),
            "stack": "horizontal",
            "size": sec.get("size") or "custom",
            "sort_order": _sort_order(sec.get("sort_order"), index),
            "width_px": sec.get("width_px") or 0,
            "height_px": sec.get("height_px") or 0,
            "layout_id": layout_id or sec.get("layout_id") or "",
            "card_mod": _parse_card_mod(sec.get("card_mod")),
            "widgets": widgets,
        }

    layouts_out: List[Dict[str, Any]] = []
    if isinstance(layouts_in, list) and layouts_in:
        for i, ly in enumerate(layouts_in):
            if not isinstance(ly, dict):
                continue
            lid = str(ly.get("id") or "") or None
            secs = []
            for si, sec in enumerate(ly.get("sections") or []):
                ns = norm_section(sec, layout_id=lid or "", index=si)
                if ns:
                    secs.append(ns)
                    sections_flat.append(ns)
            layouts_out.append(
                {
                    "id": lid,
                    "stack": ly.get("stack") or "horizontal",
                    "sort_order": _sort_order(ly.get("sort_order"), i),
                    "sections": secs,
                }
            )
    elif isinstance(doc.get("sections"), list):
        # Flat HA-ish list of sections
        for si, sec in enumerate(doc["sections"]):
            ns = norm_section(sec, index=si)
            if ns:
                sections_flat.append(ns)
        layouts_out = [
            {
                "id": None,
                "stack": "horizontal",
                "sort_order": 0,
                "sections": sections_flat,
            }
        ]
    else:
        raise ValueError("YAML must include layouts: or sections:")

    return {"layouts": layouts_out, "sections": sections_flat}
