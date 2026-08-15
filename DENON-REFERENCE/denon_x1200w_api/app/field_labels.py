"""Human-readable labels for Denon SETUP form fields & option values (English manual)."""

from __future__ import annotations

import html as html_lib
import re
from typing import Any, Dict, List

# Explicit map — prefer manual / on-screen names over raw form field ids.
FIELD_LABELS: Dict[str, str] = {
    # Audio
    "radioCinemaEq": "Cinema EQ",
    "radioLoudnessManagement": "Loudness Management",
    "radioDynamicComp": "Dynamic Compression",
    "radioDynComp": "Dynamic Compression",
    "listDynComp": "Dynamic Compression",
    "listDynamicComp": "Dynamic Compression",
    "radioDynamicCompression": "Dynamic Compression",
    "radioDynamicRange": "Dynamic Compression",
    "radioDynamicRangeComp": "Dynamic Compression",
    "radioDRC": "Dynamic Compression",
    "listDynamicRange": "Dynamic Compression",
    "textLfeLevel": "Low Frequency Effects",
    "setLfeLevel": "Set Low Frequency Effects",
    "listBilingualMode": "Bilingual Mode",
    "textAudioDelay": "Audio Delay",
    "setAudioDelay": "Set Audio Delay",
    "radioMainVolLimit": "Limit",
    "radioMainMuteLevel": "Mute Level",
    "radioMainPwOnLevel": "Power On Level",
    "textMainPwOnLevel": "Power On Level (Custom)",
    "setMainPwOnLevel": "Set Power On Level",
    "radioMainVolDisplay": "Scale",
    "listRoomEq": "MultEQ",
    "listRoomEqValue": "MultEQ Mode",
    "radioDynamicEq": "Dynamic EQ",
    "radioDynamicVol": "Dynamic Volume",
    "radioGraphicEQ": "Manual EQ",
    "listGEQSpSelection": "Speaker Selection",
    "listGEQAdjustEQ": "Adjust EQ Channel",
    "textGEQ63": "63 Hz",
    "textGEQ125": "125 Hz",
    "textGEQ250": "250 Hz",
    "textGEQ500": "500 Hz",
    "textGEQ1k": "1 kHz",
    "textGEQ2k": "2 kHz",
    "textGEQ4k": "4 kHz",
    "textGEQ8k": "8 kHz",
    "textGEQ16k": "16 kHz",
    "setAdjustEQ": "Set EQ",
    "setGEQCurveCopy": "Curve Copy",
    "setGEQSetDefaults": "Set Defaults",
    "radioSWLevelAdjustment": "Subwoofer Level Adjust",
    "radioDialogLevelAdjust": "Dialog Level Adjust",
    "listDialogLevelAdjust": "Dialog Level",
    # Video / HDMI / OSD
    "radioHdmiControl": "HDMI Control",
    "radioHdmiPwOffControl": "HDMI Pass Through",
    "radioHdmiStandbySrcControl": "Pass Through Source",
    "radioTVAudioSwitching": "TV Audio Switching",
    "radioPowerSaving": "Power Saving",
    "radioSmartMenu": "Smart Menu",
    "radioAutoLipSync": "Auto Lip Sync",
    "radioOnScreenDispFunction": "Volume / Info OSD",
    "radioOnScreenDispMasterVol": "Master Volume OSD",
    "radioOnScreenDispPlayback": "Now Playing OSD",
    "radioGuiFormat": "Format",
    "_note_tv_format": "Note",
    "_display_hdmi_audio_out": "HDMI Audio Out",
    "_display_hdmi_arc": "ARC",
    "_display_hdmi_pass": "HDMI Pass Through",
    "radioAutoLipSync": "Auto Lip Sync",
    "radioHdmiControl": "HDMI Control",
    "radioHdmiStandbySrcControl": " -Pass Through Source",
    "radioTVAudioSwitching": " -TV Audio Switching",
    "radioHdmiPwOffControl": " -Power Off Control",
    "radioPowerSaving": " -Power Saving",
    "radioSmartMenu": " -Smart Menu",
    # Inputs
    "listHdmiAssignBD": "HDMI Assign (BD)",
    "listHdmiAssignMPLAY": "HDMI Assign (Media Player)",
    "listDigitalAssignBD": "Digital Assign (BD)",
    "listDigitalAssignMPLAY": "Digital Assign (Media Player)",
    "listAnalogAssignBD": "Analog Assign (BD)",
    "listAnalogAssignMPLAY": "Analog Assign (Media Player)",
    "listVideoAssignBD": "Video Assign (BD)",
    "listVideoAssignMPLAY": "Video Assign (Media Player)",
    "listInputMode": "Input Mode",
    "listDecodeMode": "Decode Mode",
    "textSourceLevelDigital": "Source Level",
    "setSourceLevelDigital": "Set",
    "textFuncRenameBD": "Blu-ray",
    "textFuncRenameMPLAY": "Media Player",
    "setFuncRenameBD": "Set Rename BD",
    "setFuncRenameMPLAY": "Set Rename Media Player",
    "setFuncRenameAll": "Set",
    "setFuncRenameDefault": "Set Defaults",
    "buttonNet": "Set Network contents",
    "_btn_rename_defaults": "Set Defaults",
    "_btn_rename_set": "Set",
    "_btn_source_level_set": "Set",
    "_btn_set_network_contents": "Set Network contents",
    "_display_bluray_zone": "Blu-ray",
    "_note_hide_network": "Note",
    "DVD": "DVD/Blu-ray",
    "SAT/CBL": "CBL/SAT",
    "GAME": "Game",
    "TV": "TV Audio",
    "AUX1": "AUX",
    "MPLAY": "Media Player",
    "BT": "Bluetooth",
    "TUNER": "Tuner",
    "FAVORITES": "Favorites",
    "IRADIO": "Internet Radio",
    "SERVER": "Media Server",
    "USB/IPOD": "iPod/USB",
    # Speakers
    "listAmpAssignMode": "Amp Assign",
    "radioSpConfigFr": "Front",
    "radioSpConfigC": "Center",
    "radioSpConfigSr": "Surround",
    "radioSpConfigSw": "Subwoofer",
    "radioSpConfigTopMiddle": "Front Height / Top Middle",
    "textDelayTimeFl": "Front L",
    "textDelayTimeFr": "Front R",
    "textDelayTimeC": "Center",
    "textDelayTimeSl": "Surround L",
    "textDelayTimeSr": "Surround R",
    "textDelayTimeSw": "Subwoofer",
    "textDelayTimeTML": "Top Middle L",
    "textDelayTimeTMR": "Top Middle R",
    "radioDelayTimeMode": "Unit",
    "setDelayTimeAllSet": "Set All Distances",
    "textCVFL": "Front L",
    "textCVFR": "Front R",
    "textCVC": "Center",
    "textCVSL": "Surround L",
    "textCVSR": "Surround R",
    "textCVSW": "Subwoofer",
    "textCVTML": "Top Middle L",
    "textCVTMR": "Top Middle R",
    "_btn_lfe_set": "Set",
    "_btn_audio_delay_set": "Set",
    "_btn_pw_on_level_set": "Set",
    "_display_sw_level": "Subwoofer Level",
    "listRefLevelOffset": " -Reference Level Offset",
    "setCLA": "Set Channel Levels",
    "radioCrossOvers": "Speaker Selection",
    "listCrossFreqAdvFr": "Front",
    "listCrossFreqAdvC": "Center",
    "listCrossFreqAdvSr": "Surround",
    "listCrossFreqAdvTopMiddle": "Top Middle",
    "listCrossFreqAll": "All",
    "ListLpf": "LPF for LFE",
    "radioRelaySurrMode": "Subwoofer Mode",
    # Network
    "radioWifi": "Wi‑Fi",
    "listWifi_WifiSetupHow": "Wi‑Fi Setup",
    "radioNetworkSettingDHCP": "DHCP",
    "radioNetworkSettingDHCP_OnOff": "DHCP",
    "textNetworkSettingIPAddress": "IP Address",
    "textNetworkSettingSubnetMask": "Subnet Mask",
    "textNetworkSettingGateway": "Default Gateway",
    "textNetworkSettingPrimaryDNS": "Primary DNS",
    "textNetworkSettingSecondaryDNS": "Secondary DNS",
    "radioNetworkSettingProxy_OnOff": "Proxy",
    "hiddenNetworkSettingProxy_OnOff": "Proxy",
    "textNetworkSettingProxyPort": "Port",
    "buttonNetworkSettingDHCPSet": "Save",
    "buttonNetworkSettingProxySet": "Save",
    "buttonNetworkSettingTestConnection": "Connect",
    "_btn_network_settings_save": "Save",
    "_btn_network_connect": "Connect",
    "_display_connect_using": "Connect Using",
    "_note_network_settings": "Note",
    "buttonNet": "Network",
    "radioNetworkStandby": "Network Control",
    "Friendlyname": "Friendly Name",
    "listFriendlyNameTemplete": "Name Template",
    "FriendlySet": "Set Friendly Name",
    "FriendlyDef": "Default Friendly Name",
    "FriendlyErrMsg": "Friendly Name Error",
    "defBtnFriendlyName": "Default Name",
    "setBtnFriendlyName": "Set Name",
    # General
    "listOSD_Language": "Language",
    "radioECOMode": "ECO Mode",
    "radioECOPowerOnDef": "Power On Default",
    "radioECOOSD": "ECO On-Screen Display",
    "radioMainZoneABS": "MAIN ZONE",
    "_heading_auto_standby": "Auto Standby",
    "_zone2_auto_standby": "ZONE2",
    "radioUpdateNotification": "Update",
    "radioUpgradeNotification": "Upgrade",
    "radioZone2PwOnLevel": "ZONE2 Power On Level",
    "textZone2PwOnLevel": "ZONE2 Power On Level (Custom)",
    "setZone2PwOnLevel": "Set ZONE2 Power On Level",
    "radioZone2VolLevel": "ZONE2 Volume Level",
    "textZone2VolLevel": "ZONE2 Volume (Custom)",
    "setZone2VolLevel": "Set ZONE2 Volume",
    "radioZone2VolLimit": "ZONE2 Volume Limit",
    "textZoneRenameMainZone": "Main Zone Name",
    "setZoneRenameAll": "Rename All Zones",
    "setZoneRenameDefault": "Restore Default Zone Names",
    "textQuickSelectNameMainSelect1": "Quick Select 1",
    "textQuickSelectNameMainSelect2": "Quick Select 2",
    "textQuickSelectNameMainSelect3": "Quick Select 3",
    "textQuickSelectNameMainSelect4": "Quick Select 4",
    "setQuickSelectName": "Set Quick Select Name",
    "setQuickSelectNameAll": "Set All Quick Select Names",
    "setBtnQuickSelectNameDefault": "Default Quick Select Names",
    "radioDimmer": "Dimmer",
    "radioAlerts": "Notification Alerts",
    "radioUpdateNotification": "Update",
    "radioUpgradeNotification": "Upgrade",
    "radioUsageData": "Usage Data",
    "radioSetupLock": "Lock",
    "defBtnInputAssign": "Default Input Assign",
}

# Option / radio values → manual wording (case-insensitive keys stored lower).
VALUE_LABELS: Dict[str, str] = {
    "on": "On",
    "off": "Off",
    "auto": "Auto",
    "manual": "Manual",
    "last": "Last",
    "rel": "-79.5dB - 18.0dB",
    "abs": "0-98",
    "full": "Full",
    "level": "-79dB - 18dB",
    "-oodb": "Mute",
    "-∞db": "Mute",
    "-20db": "-20dB",
    "-10db": "-10dB",
    "0db": "0dB",
    "-40db": "-40dB",
    "lfe": "LFE",
    "lfe+main": "LFE+Main",
    "fl": "Front L",
    "fr": "Front R",
    "c": "Center",
    "cen": "Center",
    "sw": "Subwoofer",
    "sl": "Surround L",
    "sr": "Surround R",
    "sbl": "Surround Back L",
    "sbr": "Surround Back R",
    "fhl": "Front Height L",
    "fhr": "Front Height R",
    "tml": "Top Middle L",
    "tmr": "Top Middle R",
    "all": "All",
    "lrs": "L/R/Surround",
    "eac": "Each",
    "large": "Large",
    "small": "Small",
    "none": "None",
    "yes": "Yes",
    "no": "No",
    "meters": "Meters",
    "feet": "Feet",
    "m": "Meters",
    "ft": "Feet",
    "bright": "Bright",
    "dim": "Dim",
    "dark": "Dark",
    "light": "Light",
    "medium": "Medium",
    "heavy": "Heavy",
    "low": "Low",
    "mid": "Mid",
    "high": "High",
    "relative": "Relative",
    "absolute": "Absolute",
    "ntsc": "NTSC",
    "nts": "NTSC",
    "pal": "PAL",
    "las": "Last",
    "all": "All",
    "vdo": "Video",
    "audyssey": "Audyssey",
    "flat": "Flat",
    "reference": "Reference",
    "l/r bypass": "L/R Bypass",
    "multeq xt": "MultEQ XT",
    "multeq": "MultEQ",
    "english": "English",
    "hdmi": "HDMI",
    "digital": "Digital",
    "analog": "Analog",
}


_CAMEL = re.compile(r"(?<!^)(?=[A-Z])")
_TAG_RE = re.compile(r"<[^>]+>", re.I)
_LEAD_JUNK = re.compile(r"^[\s\u00a0\-–—·•\*]+")


def clean_display_text(value: Any) -> str:
    """Strip HTML (e.g. FONT size), entities, and leading dashes from Denon labels.

    Preserves a lone '-' / '–' which Denon uses for Off/None in select boxes.
    """
    if value is None:
        return ""
    s = str(value)
    s = _TAG_RE.sub(" ", s)
    s = html_lib.unescape(s)
    s = s.replace("\xa0", " ").replace("&nbsp;", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if s in {"-", "–", "—"}:
        return "-"
    # Keep leading minus for numeric / dB labels (Volume Scale, Limits, Mute, …)
    if re.match(r"^[\-–—]\s*\d", s):
        if s[0] in "–—":
            s = "-" + s[1:].lstrip()
        s = re.sub(r"^[\s\u00a0·•\*]+", "", s).strip()
        return s
    s = _LEAD_JUNK.sub("", s).strip()
    return s


def humanize_field_name(name: str) -> str:
    if not name:
        return name
    if name in FIELD_LABELS:
        return FIELD_LABELS[name]
    raw = name
    for prefix in ("radio", "list", "text", "setbtn", "setBtn", "button", "hidden", "defBtn"):
        if raw.startswith(prefix) and len(raw) > len(prefix):
            raw = raw[len(prefix) :]
            break
    if raw.startswith("set") and len(raw) > 3 and raw[3].isupper():
        raw = raw[3:]
    spaced = _CAMEL.sub(" ", raw).replace("_", " ").replace("/", " / ")
    spaced = re.sub(r"\s+", " ", spaced).strip()
    replacements = {
        "Eq": "EQ",
        "Eq ": "EQ ",
        "Hdmi": "HDMI",
        "Osd": "OSD",
        "Lfe": "LFE",
        "Geq": "GEQ",
        "Pw On": "Power On",
        "Pw Off": "Power Off",
        "Vol ": "Volume ",
        "Sp Config": "Speaker",
        "Gui": "GUI",
    }
    out = spaced
    for a, b in replacements.items():
        out = out.replace(a, b)
    return clean_display_text(out) or name


def humanize_value(value: Any, field_name: str = "") -> str:
    if value is None:
        return ""
    s = clean_display_text(value)
    if not s:
        return s
    key = s.lower()
    if key in VALUE_LABELS:
        return VALUE_LABELS[key]
    if key.upper() in {k.upper() for k in ("FL", "FR", "CEN", "SW", "SL", "SR", "TML", "TMR")}:
        return VALUE_LABELS.get(key, s)
    if " " in s or not re.fullmatch(r"[A-Za-z0-9_/+.\-]+", s):
        return s
    if s.isupper() and len(s) > 3:
        return s.title()
    return s


def _label_options(
    options: List[Any], field_name: str
) -> List[Any]:
    out: List[Any] = []
    for opt in options or []:
        if isinstance(opt, dict):
            val = opt.get("value", "")
            raw_label = opt.get("label")
            # Prefer manual humanize when label is empty or equals raw value
            if not raw_label or str(raw_label).strip() == str(val).strip():
                display = humanize_value(val, field_name)
            else:
                display = str(raw_label).strip()
                # Still map known codes if label is the code itself
                if display.lower() == str(val).lower():
                    display = humanize_value(val, field_name)
            item = dict(opt)
            item["label"] = display
            item["display"] = display
            out.append(item)
        else:
            out.append(
                {
                    "value": opt,
                    "label": humanize_value(opt, field_name),
                    "display": humanize_value(opt, field_name),
                    "selected": False,
                }
            )
    return out


def attach_field_labels(fields: Dict) -> Dict:
    """Copy fields with human ``label`` and readable option labels.

    Prefers live AVR ``ui_label`` (bold text from the SETUP page) over the static map.
    """
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if not isinstance(meta, dict):
            out[name] = meta
            continue
        m = dict(meta)
        raw_ui = clean_display_text(m.get("ui_label") or "")
        mapped = humanize_field_name(name)
        m["label"] = raw_ui or mapped
        opts = m.get("options")
        if isinstance(opts, list) and opts:
            if opts and not isinstance(opts[0], dict):
                m["options"] = [
                    {
                        "value": o,
                        "label": humanize_value(o, name),
                        "display": humanize_value(o, name),
                    }
                    for o in opts
                ]
            else:
                labeled = []
                for opt in opts:
                    item = dict(opt)
                    val = item.get("value", "")
                    raw_label = clean_display_text(item.get("label") or "")
                    if raw_label and raw_label.lower() != str(val).lower():
                        display = raw_label
                    else:
                        display = humanize_value(val, name)
                    item["label"] = display
                    item["display"] = display
                    labeled.append(item)
                m["options"] = labeled
        if m.get("value") is not None:
            display = None
            for opt in m.get("options") or []:
                if isinstance(opt, dict) and str(opt.get("value")) == str(m.get("value")):
                    display = opt.get("display") or opt.get("label")
                    break
            m["value_label"] = display or humanize_value(m.get("value"), name)
        out[name] = m
    return out
