#!/usr/bin/env python3
"""Build crawl coverage matrix vs AVR-X1200W English manual menu map (pp.135-137)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROT = ROOT / "protocol"

# Manual menu map (Settings section)
MANUAL = [
    # Audio
    ("Audio", "Dialog Level", "audio_dialoglevel", True),
    ("Audio", "Subwoofer Level", "audio_subwooferlevel", True),
    ("Audio", "Surr.Parameter", "audio_surroundparameter", True),
    ("Audio", "Restorer", "audio_restorer", True),
    ("Audio", "Audio Delay", "audio_audiodelay", True),
    ("Audio", "Volume", "audio_volume", True),
    ("Audio", "Audyssey (MultEQ/DynEQ/DynVol settings)", "audio_audyssey", True),
    ("Audio", "Manual EQ", "audio_graphiceq", True),
    # Video
    ("Video", "HDMI Setup", "video_hdmisetup", True),
    ("Video", "On Screen Disp.", "video_onscreendisplay", True),
    ("Video", "TV Format", "video_tvformat", True),
    # Inputs
    ("Inputs", "Input Assign", "inputs_inputassign", True),
    ("Inputs", "Source Rename", "inputs_sourcerename", True),
    ("Inputs", "Hide Sources", "inputs_hidesources", True),
    ("Inputs", "Source Level", "inputs_sourcelevel", True),
    ("Inputs", "Input Select", "inputs_inputselect", True),
    # Speakers
    (
        "Speakers",
        "Audyssey Setup (wizard)",
        "speakers_audyssey_setup",
        False,
    ),  # DO NOT crawl/start — stub only
    ("Speakers", "Manual Setup / Amp Assign", "speakers_ampassign", True),
    ("Speakers", "Manual Setup / Speaker Config.", "speakers_speakerconfig", True),
    ("Speakers", "Manual Setup / Distances", "speakers_distances", True),
    ("Speakers", "Manual Setup / Levels", "speakers_levels", True),
    ("Speakers", "Manual Setup / Crossovers", "speakers_crossovers", True),
    ("Speakers", "Manual Setup / Bass", "speakers_bass", True),
    ("Speakers", "Manual Setup / Front Speaker", "speakers_frontspeaker", True),
    # Network
    ("Network", "Information", "network_information", True),
    ("Network", "Connection", "network_connection", True),
    ("Network", "Settings", "network_settings", True),
    ("Network", "Network Control", "network_ipcontrol", True),
    ("Network", "Friendly Name", "network_friendlyname", True),
    ("Network", "Diagnostics", "network_diagnostics", True),
    ("Network", "Maintenance Mode", "network_maintenance", False),  # blocked
    # General
    ("General", "Language", "general_language", True),
    ("General", "ECO", "general_eco", True),
    ("General", "ZONE2 Setup", "general_zone2setup", True),
    ("General", "Zone Rename", "general_zonerename", True),
    ("General", "Quick Sel.Names", "general_selectnames", True),
    ("General", "Front Display", "general_frontdisplay", True),
    ("General", "Firmware (info only)", "general_firmware", True),
    ("General", "Information", "general_information", True),
    ("General", "Usage Data", "general_usagedata", True),
    ("General", "Setup Lock (read scrape only)", "general_setuplock", True),
    # Setup Assistant
    ("Setup Assistant", "Begin Setup / wizards", "setup_assistant", False),
]


def main() -> None:
    catalog = json.loads((PROT / "catalog.json").read_text(encoding="utf-8"))
    endpoints = json.loads((PROT / "endpoints.json").read_text(encoding="utf-8"))
    pages = json.loads((PROT / "protocol_map.json").read_text(encoding="utf-8")).get(
        "pages", {}
    )

    ids = {c["id"] for c in catalog}
    titles = []
    for e in endpoints:
        titles.extend(e.get("titles") or [])
    title_blob = " | ".join(titles).lower()
    page_blob = " ".join(pages.keys()).upper()

    rows = []
    for section, item, key, want_crawl in MANUAL:
        # match heuristics
        found = False
        matched = []
        for cid in ids:
            if key.replace("_", "") in cid.replace("_", "") or key in cid:
                found = True
                matched.append(cid)
        # special cases
        if key == "network_diagnostics" and "DIAGNOSTICS" in page_blob:
            found = True
            matched.append("NETWORK/DIAGNOSTICS")
        if key == "network_information":
            # often not on web menu; IP facts live under Settings
            if "NETWORK/SETTINGS" in page_blob:
                found = True
                matched.append("via NETWORK/SETTINGS (+ /api/info/network)")
        if key == "general_information" and "INFORMATION" in page_blob:
            found = True
            matched.append("GENERAL/INFORMATION")
        if key == "speakers_audyssey_setup":
            status = "STUB_ONLY_NO_WIZARD"
            note = "Do not start. Future engage toggle only; mic wizard is OSD."
        elif key == "network_maintenance":
            status = "BLOCKED"
            note = "Service technician mode — excluded"
        elif key == "setup_assistant":
            status = "BLOCKED"
            note = "Setup Assistant wizards excluded"
        elif found:
            status = "CRAWLED"
            note = ", ".join(matched[:3])
        elif want_crawl:
            status = "MISSING"
            note = "Not found on web SETUP crawl"
        else:
            status = "SKIPPED"
            note = "Intentionally not crawled"

        rows.append(
            {
                "section": section,
                "item": item,
                "key": key,
                "status": status,
                "note": note,
            }
        )

    out = {
        "source_manual": "AVR-X1200WE2_ENG_CD-ROM_IM_v00A (menu map pp.135-137)",
        "limits": [
            "No Save/Load",
            "No firmware update / web update / add feature",
            "No Setup Lock writes",
            "No network IP/DHCP/proxy writes",
            "No Audyssey Setup wizard start (engage stub only later)",
            "No Maintenance Mode",
            "No Setup Assistant",
            "Restore any temporary toggle used while scraping",
        ],
        "summary": {
            "crawled": sum(1 for r in rows if r["status"] == "CRAWLED"),
            "missing": sum(1 for r in rows if r["status"] == "MISSING"),
            "blocked_or_stub": sum(
                1 for r in rows if r["status"] in ("BLOCKED", "STUB_ONLY_NO_WIZARD", "SKIPPED")
            ),
            "catalog_endpoints": len(catalog),
            "protocol_pages": len(pages),
        },
        "items": rows,
        "future_api_stubs": [
            {
                "id": "speakers_audyssey_setup_engage",
                "method": "POST",
                "path": "/api/speakers/audyssey-setup/engage",
                "behavior": "Toggle/engage only — must NEVER auto-run Start/Begin Test/Next wizard steps",
                "status": "not_implemented_yet",
            }
        ],
    }

    (PROT / "manual_coverage.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [
        "# AVR-X1200W manual vs SETUP web crawl coverage",
        "",
        f"- Protocol pages: **{out['summary']['protocol_pages']}**",
        f"- Catalog endpoints: **{out['summary']['catalog_endpoints']}**",
        f"- Crawled: **{out['summary']['crawled']}** · Missing: **{out['summary']['missing']}** · Blocked/stub: **{out['summary']['blocked_or_stub']}**",
        "",
        "| Section | Item | Status | Note |",
        "|---------|------|--------|------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['section']} | {r['item']} | {r['status']} | {r['note']} |"
        )
    lines.append("")
    lines.append("## Limits")
    for lim in out["limits"]:
        lines.append(f"- {lim}")
    lines.append("")
    lines.append("## Future API stub (not implemented in this crawl phase)")
    lines.append(
        "- `POST /api/speakers/audyssey-setup/engage` — engage toggle only; never starts the mic wizard."
    )
    (PROT / "MANUAL_COVERAGE.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(out["summary"], indent=2))
    for r in rows:
        if r["status"] == "MISSING":
            print("MISSING:", r["section"], r["item"])


if __name__ == "__main__":
    main()
