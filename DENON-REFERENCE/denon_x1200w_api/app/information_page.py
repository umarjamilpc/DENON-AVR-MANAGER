"""Parse General → Information HTML into Denon-ordered editor fields / cards."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .field_labels import clean_display_text


def _strip_tags(text: str) -> str:
    return clean_display_text(re.sub(r"<[^>]+>", " ", text or ""))


def _h2_blocks(html: str) -> List[Tuple[str, str]]:
    parts = re.split(r"<H2[^>]*>\s*([^<]+?)\s*</H2>", html, flags=re.I)
    out: List[Tuple[str, str]] = []
    # parts: [pre, title1, body1, title2, body2, ...]
    for i in range(1, len(parts), 2):
        title = _strip_tags(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ""
        body = re.split(r"</FORM>|</BODY>", body, flags=re.I)[0]
        out.append((title, body))
    return out


def _row_cells(row_html: str) -> List[str]:
    cells = re.findall(r"<TD\b[^>]*>(.*?)</TD>", row_html, re.I | re.S)
    return [_strip_tags(c) for c in cells]


def _parse_block_rows(block: str) -> List[Dict[str, str]]:
    """Return display rows: subheading | kv. Multi empty-label values become Resolutions list."""
    rows: List[Dict[str, str]] = []
    pending_resolutions: List[str] = []

    def flush_resolutions() -> None:
        nonlocal pending_resolutions
        if pending_resolutions:
            rows.append(
                {
                    "type": "kv",
                    "label": "Resolutions",
                    "value": ", ".join(pending_resolutions),
                }
            )
            pending_resolutions = []

    for rm in re.finditer(r"<TR\b[^>]*>(.*?)</TR>", block, re.I | re.S):
        cells = _row_cells(rm.group(1))
        if not cells:
            continue
        # Single bold-only cell = subheading (HDMI Signal Info. / HDMI Monitor)
        if len(cells) == 1 and cells[0]:
            flush_resolutions()
            rows.append({"type": "subheading", "label": cells[0], "value": ""})
            continue
        label = cells[0] if cells else ""
        value = cells[1] if len(cells) > 1 else ""
        # Continuation rows for Resolutions (empty label, value only)
        if not label and value:
            pending_resolutions.append(value)
            continue
        flush_resolutions()
        if not label:
            continue
        if not value and label.upper() in ("HDMI SIGNAL INFO.", "HDMI MONITOR", "MAIN ZONE", "ZONE2"):
            rows.append({"type": "subheading", "label": label, "value": ""})
            continue
        # "MAIN ZONE" / "ZONE2" with same text as value = zone group title
        if label.upper() in ("MAIN ZONE", "ZONE2") and (
            not value or value.upper().startswith(label.upper()[:4])
        ):
            rows.append({"type": "subheading", "label": label, "value": ""})
            continue
        # Denon splits Resolutions across many rows (first labeled, rest empty label).
        if label.lower() in ("resolutions", "resolution"):
            # Single "Resolution" under HDMI Signal Info stays a normal kv
            if label.lower() == "resolution":
                rows.append(
                    {
                        "type": "kv",
                        "label": label.lstrip("- ").strip(),
                        "value": value,
                    }
                )
            else:
                pending_resolutions = [value] if value else []
            continue
        rows.append({"type": "kv", "label": label.lstrip("- ").strip(), "value": value})
    flush_resolutions()
    return rows


def parse_information_sections(html: str) -> List[Dict[str, Any]]:
    """Sections matching Denon General/Information order."""
    sections: List[Dict[str, Any]] = []
    video_pending: Optional[Dict[str, Any]] = None

    for title, body in _h2_blocks(html):
        key = title.strip().lower()
        rows = _parse_block_rows(body)

        if key == "video":
            # Split HDMI Signal Info vs HDMI Monitor into separate header bands
            signal_rows: List[Dict[str, str]] = []
            monitor_rows: List[Dict[str, str]] = []
            bucket = signal_rows
            for row in rows:
                if row.get("type") == "subheading" and "monitor" in row.get("label", "").lower():
                    bucket = monitor_rows
                    continue
                if row.get("type") == "subheading" and "signal" in row.get("label", "").lower():
                    bucket = signal_rows
                    # Keep Signal Info as subheading under Video
                    signal_rows.append(row)
                    continue
                bucket.append(row)

            sections.append(
                {
                    "id": "video",
                    "title": "Video",
                    "items": [
                        {"label": r["label"], "value": r.get("value", ""), "kind": r["type"]}
                        for r in signal_rows
                    ],
                }
            )
            if monitor_rows:
                sections.append(
                    {
                        "id": "hdmi_monitor",
                        "title": "HDMI Monitor",
                        "items": [
                            {
                                "label": r["label"],
                                "value": r.get("value", ""),
                                "kind": r["type"],
                            }
                            for r in monitor_rows
                            if r.get("type") != "subheading"
                            or r.get("label", "").lower() != "hdmi monitor"
                        ],
                    }
                )
            continue

        if key == "notifications":
            # Alerts radios are live form controls; skip static empty facts here
            sections.append(
                {
                    "id": "alerts",
                    "title": "Notifications",
                    "items": [],
                    "has_alerts_control": True,
                }
            )
            continue

        if key == "firmware":
            items = []
            for r in rows:
                if r.get("type") != "kv":
                    continue
                lab = r["label"]
                if re.search(r"update\s*notification|upgrade\s*notification", lab, re.I):
                    continue
                items.append({"label": lab, "value": r.get("value", ""), "kind": "kv"})
            sections.append({"id": "firmware", "title": "Firmware", "items": items})
            continue

        sid = {
            "audio": "audio",
            "zone": "zones",
            "zone2": "zones",
        }.get(key, re.sub(r"[^a-z0-9]+", "_", key).strip("_") or "section")

        sections.append(
            {
                "id": sid,
                "title": title if title.upper() != "ZONE" else "ZONE",
                "items": [
                    {"label": r["label"], "value": r.get("value", ""), "kind": r["type"]}
                    for r in rows
                ],
            }
        )

    if video_pending:
        sections.append(video_pending)
    return sections


def build_information_editor_fields(
    html: str, form_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Field dict for Setup editor matching Denon Information layout."""
    form_fields = form_fields or {}
    out: Dict[str, Any] = {}
    for sec in parse_information_sections(html):
        hid = f"_heading_info_{sec['id']}"
        out[hid] = {
            "type": "heading",
            "label": sec["title"],
            "ui_label": sec["title"],
            "value": "",
            "options": [],
            "inactive": False,
        }
        for i, item in enumerate(sec.get("items") or []):
            kind = item.get("kind") or "kv"
            key = f"_info_{sec['id']}_{i}"
            if kind == "subheading":
                out[key] = {
                    "type": "subheading",
                    "label": item["label"],
                    "ui_label": item["label"],
                    "value": "",
                    "options": [],
                    "inactive": False,
                }
            else:
                out[key] = {
                    "type": "display",
                    "label": item["label"],
                    "ui_label": item["label"],
                    "value": item.get("value") or "",
                    "options": [],
                    "inactive": False,
                }
        if sec.get("has_alerts_control") and isinstance(
            form_fields.get("radioAlerts"), dict
        ):
            alert = dict(form_fields["radioAlerts"])
            alert["label"] = "Notification Alerts"
            alert["ui_label"] = "Notification Alerts"
            out["radioAlerts"] = alert

    # Fallback if parse missed alerts
    if "radioAlerts" not in out and isinstance(form_fields.get("radioAlerts"), dict):
        out["_heading_info_alerts"] = {
            "type": "heading",
            "label": "Notifications",
            "ui_label": "Notifications",
            "value": "",
            "options": [],
            "inactive": False,
        }
        alert = dict(form_fields["radioAlerts"])
        alert["label"] = "Notification Alerts"
        alert["ui_label"] = "Notification Alerts"
        out["radioAlerts"] = alert

    return out


def sections_as_dashboard_cards(html: str) -> List[Dict[str, Any]]:
    """Card list for Info dashboard / filtered setup_info views."""
    cards: List[Dict[str, Any]] = []
    for sec in parse_information_sections(html):
        items = []
        for item in sec.get("items") or []:
            if item.get("kind") == "subheading":
                items.append(
                    {
                        "label": item["label"],
                        "value": "",
                        "kind": "subheading",
                    }
                )
            else:
                items.append(
                    {
                        "label": item["label"],
                        "value": item.get("value") or "",
                    }
                )
        cards.append(
            {
                "id": sec["id"],
                "title": sec["title"],
                "items": items,
            }
        )
    return cards
