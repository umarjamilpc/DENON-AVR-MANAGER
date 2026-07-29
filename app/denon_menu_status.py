"""Live Denon SETUP submenu availability (greyed items).

Denon renders unavailable items as grey text (``#999999``) without an
``<a href>`` in each section's ``MENU/d_right_*.asp`` page. Examples:
Restorer (needs a compressed PCM source), Front Speaker (needs Bi-Amp /
Front B amp assign), ZONE2 Setup (needs Amp Assign = ZONE2).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .denon_client import DenonSetupClient
from .field_labels import clean_display_text

SETUP_LOCK_READ_URL = "/SETUP/GENERAL/SETUPLOCK/d_general.asp"
SETUP_LOCK_ENDPOINT_ID = "general_setuplock_s_general"
SETUP_LOCK_MENU_ID = "general_lock"
SETUP_LOCK_REASON = (
    "Setup Lock is On. Open Setup Lock and set Off to change settings."
)

# Section overview frames Denon uses for grey/active submenu state.
SUBMENU_PAGES: Tuple[str, ...] = (
    "/SETUP/AUDIO/MENU/d_right_audio.asp",
    "/SETUP/VIDEO/MENU/d_right_video.asp",
    "/SETUP/INPUTS/MENU/d_right_inputsetup.asp",
    "/SETUP/SPEAKERS/MENU/d_right_speakers.asp",
    "/SETUP/NETWORK/MENU/d_right_network.asp",
    "/SETUP/GENERAL/MENU/d_right_general.asp",
)

# Normalize Denon list text → our menu node id
LABEL_TO_MENU_ID: Dict[str, str] = {
    "dialog level": "audio_dialog",
    "dialog level adjust": "audio_dialog",
    "subwoofer level": "audio_subwoofer",
    "subwoofer level adjust": "audio_subwoofer",
    "surround parameter": "audio_surround",
    "surr.parameter": "audio_surround",
    "restorer": "audio_restorer",
    "audio delay": "audio_delay",
    "volume": "audio_volume",
    "bilingual mode": "audio_bilingual",
    "audyssey": "audio_audyssey",
    "manual eq": "audio_manual_eq",
    "hdmi setup": "video_hdmi",
    "on screen display": "video_osd",
    "on screen disp.": "video_osd",
    "tv format": "video_tv",
    "4k/tv format": "video_tv",
    "input assign": "inputs_assign",
    "source rename": "inputs_rename",
    "hide sources": "inputs_hide",
    "source level": "inputs_level",
    "input select": "inputs_select",
    "amp assign": "speakers_amp",
    "speaker config.": "speakers_config",
    "speaker config": "speakers_config",
    "distances": "speakers_dist",
    "levels": "speakers_levels",
    "crossovers": "speakers_xo",
    "bass": "speakers_bass",
    "front speaker": "speakers_front",
    "connection": "network_connection",
    "settings": "network_settings",
    "network control": "network_control",
    "friendly name": "network_friendly",
    "diagnostics": "network_diag",
    "information": "network_info",  # ambiguous; handled per section
    "language": "general_lang",
    "eco": "general_eco",
    "zone2 setup": "general_zone2",
    "zone rename": "general_zrename",
    "quick select names": "general_qsel",
    "quick sel.names": "general_qsel",
    "front display": "general_front",
    "firmware": "general_fw",
    "usage data": "general_usage",
    "setup lock": "general_lock",
}

_GREY_RE = re.compile(r"color\s*=\s*['\"]?#999999", re.I)
_LI_RE = re.compile(r"<li\b[^>]*>(.*?)</li>", re.I | re.S)
_A_RE = re.compile(r"<a\b[^>]*href\s*=\s*['\"][^'\"]+['\"]", re.I)


def _norm_label(text: str) -> str:
    s = clean_display_text(text)
    s = re.sub(r"^(audio|video|inputs|speakers|network|general)[\s/]+", "", s, flags=re.I)
    s = re.sub(r"^speakers/manual setup\s+", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip().lower()


def parse_submenu_items(html: str) -> List[Dict[str, Any]]:
    """Return [{label, inactive}] from a Denon MENU/d_right_*.asp page."""
    items: List[Dict[str, Any]] = []
    for m in _LI_RE.finditer(html or ""):
        chunk = m.group(1)
        text = clean_display_text(re.sub(r"<[^>]+>", " ", chunk))
        if not text:
            continue
        has_link = bool(_A_RE.search(chunk))
        is_grey = bool(_GREY_RE.search(chunk))
        # True unavailable: grey text with no navigation link
        inactive = is_grey and not has_link
        items.append({"label": text, "inactive": inactive, "has_link": has_link})
    return items


def resolve_menu_id(label: str, section_hint: str = "") -> Optional[str]:
    key = _norm_label(label)
    if key == "information":
        if section_hint == "network":
            return "network_info"
        if section_hint == "general":
            return "general_info"
        return None
    if key in LABEL_TO_MENU_ID:
        return LABEL_TO_MENU_ID[key]
    # Fuzzy contains
    for needle, mid in LABEL_TO_MENU_ID.items():
        if needle in key or key in needle:
            return mid
    return None


def scrape_live_menu_availability(client: DenonSetupClient) -> Dict[str, Dict[str, Any]]:
    """Probe Denon section menus; return menu_id → {inactive, inactive_reason}."""
    flags: Dict[str, Dict[str, Any]] = {}
    section_for_path = {
        "/SETUP/AUDIO/MENU/d_right_audio.asp": "audio",
        "/SETUP/VIDEO/MENU/d_right_video.asp": "video",
        "/SETUP/INPUTS/MENU/d_right_inputsetup.asp": "inputs",
        "/SETUP/SPEAKERS/MENU/d_right_speakers.asp": "speakers",
        "/SETUP/NETWORK/MENU/d_right_network.asp": "network",
        "/SETUP/GENERAL/MENU/d_right_general.asp": "general",
    }
    for path in SUBMENU_PAGES:
        section = section_for_path.get(path, "")
        try:
            html = client.get(path)
        except Exception:  # noqa: BLE001
            continue
        for item in parse_submenu_items(html):
            mid = resolve_menu_id(item["label"], section)
            if not mid:
                continue
            if item["inactive"]:
                flags[mid] = {
                    "inactive": True,
                    "inactive_reason": (
                        f"{item['label']} is unavailable with the current AVR input / "
                        "amp assign / signal — Denon greys it out until required settings apply."
                    ),
                }
            elif mid not in flags:
                flags[mid] = {"inactive": False}
    return flags


def is_setup_locked(client: DenonSetupClient) -> bool:
    """True when AVR General → Setup Lock is On."""
    try:
        page = client.read_page(SETUP_LOCK_READ_URL)
        val = ((page.get("fields") or {}).get("radioSetupLock") or {}).get("value")
        return str(val or "").upper() == "ON"
    except Exception:  # noqa: BLE001
        return False


def apply_setup_lock_to_menu(
    sections: List[Dict[str, Any]], locked: bool
) -> None:
    """Grey every menu leaf except Setup Lock when lock is On."""
    if not locked:
        return

    def walk(nodes: List[Dict[str, Any]]) -> None:
        for n in nodes or []:
            children = n.get("children") or []
            if children:
                walk(children)
                continue
            if n.get("id") == SETUP_LOCK_MENU_ID:
                n["inactive"] = False
                n.pop("inactive_reason", None)
                n.pop("setup_lock_blocked", None)
                continue
            n["inactive"] = True
            n["inactive_reason"] = SETUP_LOCK_REASON
            n["setup_lock_blocked"] = True

    walk(sections)


def page_has_editable_controls(fields: Dict[str, Any]) -> bool:
    """False when Denon served an empty shell (e.g. Restorer with no Mode radios)."""
    skip_types = {"hidden", "button", "submit", "heading", "display", "note"}
    skip_names = {"setPureDirectOn", "setSetupLock"}
    for name, meta in (fields or {}).items():
        if name in skip_names:
            continue
        if (
            name.startswith("_heading_")
            or name.startswith("_display_")
            or name.startswith("_zone2_")
            or name.startswith("_note_")
            or name.startswith("_btn_")
        ):
            continue
        if not isinstance(meta, dict):
            continue
        if meta.get("type") in skip_types:
            continue
        if name.lower().startswith("setbtn"):
            continue
        if meta.get("inactive") or meta.get("disabled"):
            continue
        return True
    return False
