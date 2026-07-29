"""Denon AVR Setup menu tree — English manual OSD hierarchy (pp.135–137).

Maps each leaf to one scraped web endpoint (or a special action).
Scraped duplicate ``*_r_*`` read forms and frameset title bugs ("Setup Menu")
are avoided here on purpose.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from .host_utils import rewrite_endpoint
from .protocol_loader import get_endpoint, load_catalog
from .safety import annotate_catalog_item

# Manual top-level SETUP order
MENU_TREE: List[Dict[str, Any]] = [
    {
        "id": "audio",
        "label": "Audio",
        "children": [
            {
                "id": "audio_dialog",
                "label": "Dialog Level Adjust",
                "endpoint_id": "audio_dialoglevel_s_audio",
            },
            {
                "id": "audio_subwoofer",
                "label": "Subwoofer Level Adjust",
                "endpoint_id": "audio_subwooferlevel_s_audio",
            },
            {
                "id": "audio_surround",
                "label": "Surround Parameter",
                "endpoint_id": "audio_surroundparameter_s_audio",
            },
            {"id": "audio_restorer", "label": "Restorer", "endpoint_id": "audio_restorer_s_audio"},
            {"id": "audio_delay", "label": "Audio Delay", "endpoint_id": "audio_audiodelay_s_audio"},
            {"id": "audio_volume", "label": "Volume", "endpoint_id": "audio_volume_s_audio"},
            {
                "id": "audio_bilingual",
                "label": "Bilingual Mode",
                "endpoint_id": "audio_bilingualmode_s_audio",
            },
            {
                "id": "audio_audyssey",
                "label": "Audyssey",
                "endpoint_id": "audio_audyssey_s_audio",
                "note": "MultEQ / Dynamic EQ / Dynamic Volume settings (not the Speakers wizard).",
            },
            {
                "id": "audio_manual_eq",
                "label": "Manual EQ",
                "endpoint_id": "audio_graphiceq_s_audio",
                "ui_hint": "manual-eq",
            },
        ],
    },
    {
        "id": "video",
        "label": "Video",
        "children": [
            {"id": "video_hdmi", "label": "HDMI Setup", "endpoint_id": "video_hdmisetup_s_video"},
            {
                "id": "video_osd",
                "label": "On Screen Display",
                "endpoint_id": "video_onscreendisplay_s_video",
            },
            {"id": "video_tv", "label": "TV Format", "endpoint_id": "video_tvformat_s_video"},
        ],
    },
    {
        "id": "inputs",
        "label": "Inputs",
        "children": [
            {
                "id": "inputs_assign",
                "label": "Input Assign",
                "endpoint_id": "inputs_inputassign_s_inputassign",
                "ui_hint": "input-assign",
            },
            {
                "id": "inputs_rename",
                "label": "Source Rename",
                "endpoint_id": "inputs_sourcerename_s_rename",
            },
            {
                "id": "inputs_hide",
                "label": "Hide Sources",
                "endpoint_id": "inputs_hidesources_s_delete",
            },
            {
                "id": "inputs_level",
                "label": "Source Level",
                "endpoint_id": "inputs_sourcelevel_s_inputsetup",
            },
            {
                "id": "inputs_select",
                "label": "Input Select",
                "endpoint_id": "inputs_inputselect_s_inputsetup",
            },
        ],
    },
    {
        "id": "speakers",
        "label": "Speakers",
        "children": [
            {
                "id": "speakers_audyssey_setup",
                "label": "Audyssey Setup",
                "action": "audyssey_setup_engage",
                "endpoint_id": None,
                "write_allowed": False,
                "note": (
                    "Mic calibration wizard. Engage stub only — never starts Begin Test. "
                    "Use the AVR OSD / calibration mic for real setup."
                ),
            },
            {
                "id": "speakers_manual_setup",
                "label": "Manual Setup",
                "children": [
                    {
                        "id": "speakers_amp",
                        "label": "Amp Assign",
                        "endpoint_id": "speakers_ampassign_s_speakersetup",
                    },
                    {
                        "id": "speakers_config",
                        "label": "Speaker Config.",
                        "endpoint_id": "speakers_speakerconfig_s_speakersetup",
                    },
                    {
                        "id": "speakers_dist",
                        "label": "Distances",
                        "endpoint_id": "speakers_distances_s_speakersetup",
                    },
                    {
                        "id": "speakers_levels",
                        "label": "Levels",
                        "endpoint_id": "speakers_levels_s_speakersetup",
                    },
                    {
                        "id": "speakers_xo",
                        "label": "Crossovers",
                        "endpoint_id": "speakers_crossovers_s_speakersetup",
                    },
                    {
                        "id": "speakers_bass",
                        "label": "Bass",
                        "endpoint_id": "speakers_bass_s_speakersetup",
                    },
                    {
                        "id": "speakers_front",
                        "label": "Front Speaker",
                        "endpoint_id": "speakers_frontspeaker_s_speakersetup",
                    },
                ],
            },
        ],
    },
    {
        "id": "network",
        "label": "Network",
        "children": [
            {
                "id": "network_connection",
                "label": "Connection",
                "endpoint_id": "network_connection_s_network_setting_dhcp",
                "note": "Wi‑Fi / Connect. Saving can drop the network — explicit Save/Connect only (no live apply).",
            },
            {
                "id": "network_settings",
                "label": "Settings",
                "endpoint_id": "network_settings_s_network_setting_dhcp",
                "note": "DHCP / IP / Proxy. Saving resets the network (~60s). Explicit Save only — do not change unless intended.",
            },
            {
                "id": "network_control",
                "label": "Network Control",
                "endpoint_id": "network_ipcontrol_s_network",
            },
            {
                "id": "network_friendly",
                "label": "Friendly Name",
                "endpoint_id": "network_friendlyname_s_network",
            },
            {
                "id": "network_info",
                "label": "Information",
                "action": "setup_info",
                "info_page": "network",
                "endpoint_id": None,
                "write_allowed": False,
                "hidden": True,
                "note": "Not on X1200W Network menu — network facts stay under Info tab.",
            },
            {
                "id": "network_diag",
                "label": "Diagnostics",
                "endpoint_id": "network_diagnostics_s_network",
                "hidden": True,
                "note": "Not on X1200W Network menu.",
            },
            {
                "id": "network_maintenance",
                "label": "Maintenance Mode",
                "action": "blocked",
                "endpoint_id": None,
                "write_allowed": False,
                "hidden": True,
                "note": "Service mode — excluded from UI and writes.",
            },
        ],
    },
    {
        "id": "general",
        "label": "General",
        "children": [
            {"id": "general_lang", "label": "Language", "endpoint_id": "general_language_s_general"},
            {"id": "general_eco", "label": "ECO", "endpoint_id": "general_eco_s_general"},
            {
                "id": "general_zone2",
                "label": "ZONE2 Setup",
                "endpoint_id": "general_zone2setup_s_general",
            },
            {
                "id": "general_zrename",
                "label": "Zone Rename",
                "endpoint_id": "general_zonerename_s_general",
            },
            {
                "id": "general_qsel",
                "label": "Quick Sel.Names",
                "endpoint_id": "general_selectnames_s_general",
            },
            {
                "id": "general_front",
                "label": "Front Display",
                "endpoint_id": "general_frontdisplay_s_general",
            },
            {
                "id": "general_fw",
                "label": "Firmware",
                "endpoint_id": "general_firmware_s_firmware",
                "note": "Notifications, Update / Add New Feature / Web Update, and Local Upload (confirm required).",
            },
            {
                "id": "general_info",
                "label": "Information",
                "endpoint_id": "general_information_s_information",
                "note": "Status page matching Denon Information. Notification Alerts On/Off writable.",
            },
            {
                "id": "general_usage",
                "label": "Usage Data",
                "endpoint_id": "general_usagedata_s_general",
            },
            {
                "id": "general_lock",
                "label": "Setup Lock",
                "endpoint_id": "general_setuplock_s_general",
                "note": "Lock On/Off (unlocked). When On, only Setup Lock stays available until you set Off.",
            },
        ],
    },
]

# Raw endpoint ids that are intentionally omitted from the primary menu
# (duplicates, legacy helper pages, service stubs).
OMIT_FROM_FLAT_CATALOG = {
    "18_others_s_otherspuredirect",
    "18_others_s_otherssetuplock",
    "general_firmware_r_firmware",
    "network_connection_r_network_setting_dhcp",
    "network_settings_r_network_setting_dhcp",
}


def _label_lookup() -> Dict[str, str]:
    out: Dict[str, str] = {}

    def walk(nodes: List[Dict[str, Any]]) -> None:
        for n in nodes:
            eid = n.get("endpoint_id")
            if eid:
                out[eid] = n["label"]
            if n.get("children"):
                walk(n["children"])

    walk(MENU_TREE)
    return out


DISPLAY_TITLES = _label_lookup()


def _annotate_node(node: Dict[str, Any], base: Optional[str]) -> Dict[str, Any]:
    out = {k: v for k, v in node.items() if k != "children"}
    eid = out.get("endpoint_id")
    if eid:
        try:
            item = get_endpoint(eid, base) if base else get_endpoint(eid)
            item = annotate_catalog_item(item)
            # Prefer manual label over scraped title
            item["title"] = out.get("label") or item.get("title")
            item["menu_id"] = out["id"]
            if out.get("note"):
                item["note"] = out["note"]
            if "write_allowed" in out and out["write_allowed"] is False:
                item["write_allowed"] = False
                item["write_block_reason"] = out.get("note") or item.get(
                    "write_block_reason"
                )
            out["endpoint"] = item
            out["write_allowed"] = item["write_allowed"]
            out["write_block_reason"] = item.get("write_block_reason")
        except KeyError:
            out["endpoint"] = None
            out["missing_endpoint"] = True
            out["write_allowed"] = False
    elif out.get("action") == "audyssey_setup_engage":
        out["write_allowed"] = False
        out["engage_path"] = "/api/speakers/audyssey-setup/engage"
    elif out.get("action") in (
        "info_network",
        "info_firmware",
        "info_dashboard",
        "setup_info",
        "blocked",
    ):
        out["write_allowed"] = False
    else:
        out.setdefault("write_allowed", False)

    if node.get("children"):
        out["children"] = [
            _annotate_node(c, base)
            for c in node["children"]
            if not c.get("hidden")
        ]
    return out


def build_menu(base: Optional[str] = None, *, include_extras: bool = True) -> Dict[str, Any]:
    tree: List[Dict[str, Any]] = []
    for section in MENU_TREE:
        sec = {
            "id": section["id"],
            "label": section["label"],
            "children": [],
        }
        for child in section.get("children") or []:
            if child.get("hidden"):
                continue
            if child.get("extra") and not include_extras:
                continue
            sec["children"].append(_annotate_node(deepcopy(child), base))
        tree.append(sec)
    return {
        "source": "AVR-X1200W English manual menu map (Settings)",
        "sections": tree,
    }


def flatten_menu_leaves(base: Optional[str] = None) -> List[Dict[str, Any]]:
    """Flat catalog in manual order — one entry per menu leaf with an endpoint."""
    leaves: List[Dict[str, Any]] = []

    def walk(nodes: List[Dict[str, Any]], section_label: str) -> None:
        for n in nodes:
            if n.get("hidden"):
                continue
            if n.get("children"):
                walk(n["children"], section_label)
                continue
            eid = n.get("endpoint_id")
            if not eid:
                continue
            try:
                item = get_endpoint(eid, base) if base else get_endpoint(eid)
            except KeyError:
                continue
            item = annotate_catalog_item(item)
            item["title"] = n["label"]
            item["menu_id"] = n["id"]
            item["menu_section"] = section_label
            item["section"] = section_label.upper().replace(" ", "_")
            if n.get("note"):
                item["note"] = n["note"]
            if n.get("write_allowed") is False:
                item["write_allowed"] = False
                item["write_block_reason"] = n.get("note") or item.get(
                    "write_block_reason"
                )
            leaves.append(item)

    for section in MENU_TREE:
        walk(section.get("children") or [], section["label"])
    return leaves


def cleaned_catalog(base: Optional[str] = None) -> List[Dict[str, Any]]:
    """Prefer menu-ordered leaves; fall back to raw catalog with fixed titles."""
    leaves = flatten_menu_leaves(base)
    seen = {i["id"] for i in leaves}
    # Append any leftover non-omitted endpoints not in the menu (safety net)
    raw = load_catalog()
    for item in raw:
        if item["id"] in seen or item["id"] in OMIT_FROM_FLAT_CATALOG:
            continue
        annotated = annotate_catalog_item(
            rewrite_endpoint(item, base) if base else dict(item)
        )
        annotated["title"] = DISPLAY_TITLES.get(item["id"], annotated.get("title"))
        if annotated["title"] in (None, "", "Setup Menu", "OTHERS"):
            annotated["title"] = item["id"]
        leaves.append(annotated)
    return leaves
