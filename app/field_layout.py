"""Field order + active/inactive (grey-out) rules that mirror Denon SETUP UI.

Denon often hides or greys controls until a parent option is selected; the HTML
rarely sets the HTML ``disabled`` attribute, so we apply these gates ourselves.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Preferred display order by endpoint id (field names that appear on the page).
FIELD_ORDER: Dict[str, Sequence[str]] = {
    "audio_volume_s_audio": (
        "radioMainVolDisplay",
        "radioMainVolLimit",
        "radioMainPwOnLevel",
        "textMainPwOnLevel",
        "_btn_pw_on_level_set",
        "radioMainMuteLevel",
    ),
    "audio_dialoglevel_s_audio": (
        "radioDialogLevelAdjust",
        "listDialogLevelAdjust",
    ),
    "audio_subwooferlevel_s_audio": (
        "radioSWLevelAdjustment",
        "listSWLevelAdjustment",
        "textSWLevelAdjustment",
        "_display_sw_level",
    ),
    "audio_surroundparameter_s_audio": (
        "radioCinemaEq",
        "radioLoudnessManagement",
        "radioDynamicComp",
        "radioDynComp",
        "listDynComp",
        "listDynamicComp",
        "radioDynamicCompression",
        "radioDynamicRange",
        "radioDynamicRangeComp",
        "radioDRC",
        "listDynamicRange",
        "textLfeLevel",
        "_btn_lfe_set",
    ),
    "audio_audiodelay_s_audio": (
        "textAudioDelay",
        "_btn_audio_delay_set",
    ),
    "audio_audyssey_s_audio": (
        "listRoomEq",
        "radioDynamicEq",
        "listRefLevelOffset",
        "radioDynamicVol",
    ),
    "speakers_crossovers_s_speakersetup": (
        "radioCrossOvers",
        "listCrossFreqAll",
        "listCrossFreqAdvFr",
        "listCrossFreqAdvC",
        "listCrossFreqAdvSr",
        "listCrossFreqAdvTopMiddle",
    ),
    "speakers_speakerconfig_s_speakersetup": (
        "radioSpConfigFr",
        "radioSpConfigC",
        "radioSpConfigSw",
        "radioSpConfigSr",
        "radioSpConfigTopMiddle",
    ),
    "speakers_distances_s_speakersetup": (
        "radioDelayTimeMode",
        "textDelayTimeFl",
        "textDelayTimeFr",
        "textDelayTimeC",
        "textDelayTimeSl",
        "textDelayTimeSr",
        "textDelayTimeSw",
        "textDelayTimeTML",
        "textDelayTimeTMR",
        "_btn_distances_set",
    ),
    "network_friendlyname_s_network": (
        "listFriendlyNameTemplete",
        "Friendlyname",
        "_btn_friendly_set",
        "_btn_friendly_defaults",
    ),
    "general_zonerename_s_general": (
        "_btn_zone_rename_defaults",
        "textZoneRenameMainZone",
        "_btn_zone_rename_set",
    ),
    "general_selectnames_s_general": (
        "_btn_quick_select_defaults",
        "textQuickSelectNameMainSelect1",
        "textQuickSelectNameMainSelect2",
        "textQuickSelectNameMainSelect3",
        "textQuickSelectNameMainSelect4",
        "_btn_quick_select_set",
    ),
    "speakers_levels_s_speakersetup": (
        # Denon Levels UI order (clockwise / on-screen sequence) + Set
        "textCVFL",
        "textCVC",
        "textCVFR",
        "textCVSR",
        "textCVSL",
        "textCVTMR",
        "textCVTML",
        "textCVSW",
        "_btn_levels_set",
    ),
    "speakers_bass_s_speakersetup": (
        "radioRelaySurrMode",
        "ListLpf",
    ),
    "inputs_sourcerename_s_rename": (
        "_btn_rename_defaults",
        "textFuncRenameBD",
        "textFuncRenameMPLAY",
        "_btn_rename_set",
    ),
    "inputs_hidesources_s_delete": (
        "SAT/CBL",
        "DVD",
        "_display_bluray_zone",
        "GAME",
        "AUX1",
        "MPLAY",
        "USB/IPOD",
        "TUNER",
        "TV",
        "BT",
        "_note_hide_network",
        "FAVORITES",
        "IRADIO",
        "SERVER",
        "_btn_set_network_contents",
    ),
    "inputs_sourcelevel_s_inputsetup": (
        "textSourceLevelDigital",
        "_btn_source_level_set",
    ),
    "general_zone2setup_s_general": (
        "radioZone2VolLevel",
        "textZone2VolLevel",
        "radioZone2VolLimit",
        "radioZone2PwOnLevel",
        "textZone2PwOnLevel",
    ),
    "general_eco_s_general": (
        "radioECOMode",
        "radioECOPowerOnDef",
        "radioECOOSD",
        "_heading_auto_standby",
        "radioMainZoneABS",
        "_zone2_auto_standby",
    ),
    "general_firmware_s_firmware": (
        "_heading_fw_update",
        "_btn_fw_update",
        "_heading_fw_notifications",
        "radioUpdateNotification",
        "radioUpgradeNotification",
        "_heading_fw_add_feature",
        "_btn_fw_add_feature",
        "_heading_fw_web_update",
        "_btn_fw_web_update",
        "_heading_fw_local",
        "_fw_local_upload",
    ),
    "general_setuplock_s_general": ("radioSetupLock",),
    "network_settings_s_network_setting_dhcp": (
        "radioNetworkSettingDHCP",
        "textNetworkSettingIPAddress",
        "textNetworkSettingSubnetMask",
        "textNetworkSettingGateway",
        "textNetworkSettingPrimaryDNS",
        "textNetworkSettingSecondaryDNS",
        "radioNetworkSettingProxy_OnOff",
        "textNetworkSettingProxyPort",
        "_btn_network_settings_save",
        "_note_network_settings",
    ),
    "network_connection_s_network_setting_dhcp": (
        "radioWifi",
        "_display_connect_using",
        "listWifi_WifiSetupHow",
        "_btn_network_connect",
    ),
    "video_tvformat_s_video": (
        "radioGuiFormat",
        "_note_tv_format",
    ),
    "video_hdmisetup_s_video": (
        "radioAutoLipSync",
        "_display_hdmi_audio_out",
        "radioHdmiControl",
        "_display_hdmi_arc",
        "_display_hdmi_pass",
        "radioHdmiStandbySrcControl",
        "radioTVAudioSwitching",
        "radioHdmiPwOffControl",
        "radioPowerSaving",
        "radioSmartMenu",
    ),
}

# Child field → parent field must be one of the values for the child to be active.
# If the parent is missing from the form, children stay active.
FIELD_GATES: Dict[str, Tuple[str, Sequence[str]]] = {
    # Crossovers: individual freqs only when Speaker Selection = Individual
    "listCrossFreqAdvFr": ("radioCrossOvers", ("IDV",)),
    "listCrossFreqAdvC": ("radioCrossOvers", ("IDV",)),
    "listCrossFreqAdvSr": ("radioCrossOvers", ("IDV",)),
    "listCrossFreqAdvTopMiddle": ("radioCrossOvers", ("IDV",)),
    "listCrossFreqAll": ("radioCrossOvers", ("ALL",)),
    # Volume: custom Power On dB only when mode = Level
    "textMainPwOnLevel": ("radioMainPwOnLevel", ("Level",)),
    "setMainPwOnLevel": ("radioMainPwOnLevel", ("Level",)),
    # Dialog / Subwoofer level adjust
    "listDialogLevelAdjust": ("radioDialogLevelAdjust", ("ON",)),
    "listSWLevelAdjustment": ("radioSWLevelAdjustment", ("ON",)),
    "textSWLevelAdjustment": ("radioSWLevelAdjustment", ("ON",)),
    "listRefLevelOffset": ("radioDynamicEq", ("ON",)),
    # Dynamic Compression only when Loudness Management is On
    "radioDynamicComp": ("radioLoudnessManagement", ("ON",)),
    "radioDynComp": ("radioLoudnessManagement", ("ON",)),
    "listDynComp": ("radioLoudnessManagement", ("ON",)),
    "listDynamicComp": ("radioLoudnessManagement", ("ON",)),
    "radioDynamicCompression": ("radioLoudnessManagement", ("ON",)),
    "radioDynamicRange": ("radioLoudnessManagement", ("ON",)),
    "radioDynamicRangeComp": ("radioLoudnessManagement", ("ON",)),
    "radioDRC": ("radioLoudnessManagement", ("ON",)),
    "listDynamicRange": ("radioLoudnessManagement", ("ON",)),
    # ZONE2
    "textZone2VolLevel": ("radioZone2VolLevel", ("–––", "---", "Level", "CUS", "Custom")),
    "textZone2PwOnLevel": ("radioZone2PwOnLevel", ("Level", "–––", "---")),
    # Manual EQ bands (also gated in dedicated EQ UI)
    "listGEQAdjustEQ": ("radioGraphicEQ", ("ON",)),
    "listGEQSpSelection": ("radioGraphicEQ", ("ON",)),
    "textGEQ63": ("radioGraphicEQ", ("ON",)),
    "textGEQ125": ("radioGraphicEQ", ("ON",)),
    "textGEQ250": ("radioGraphicEQ", ("ON",)),
    "textGEQ500": ("radioGraphicEQ", ("ON",)),
    "textGEQ1k": ("radioGraphicEQ", ("ON",)),
    "textGEQ2k": ("radioGraphicEQ", ("ON",)),
    "textGEQ4k": ("radioGraphicEQ", ("ON",)),
    "textGEQ8k": ("radioGraphicEQ", ("ON",)),
    "textGEQ16k": ("radioGraphicEQ", ("ON",)),
    # Network Settings: IP fields only when DHCP Off
    "textNetworkSettingIPAddress": ("radioNetworkSettingDHCP", ("OFF",)),
    "textNetworkSettingSubnetMask": ("radioNetworkSettingDHCP", ("OFF",)),
    "textNetworkSettingGateway": ("radioNetworkSettingDHCP", ("OFF",)),
    "textNetworkSettingPrimaryDNS": ("radioNetworkSettingDHCP", ("OFF",)),
    "textNetworkSettingSecondaryDNS": ("radioNetworkSettingDHCP", ("OFF",)),
    "textNetworkSettingProxyPort": ("radioNetworkSettingProxy_OnOff", ("ADR", "NAM")),
    # HDMI Setup children active when HDMI Control is On
    "radioHdmiStandbySrcControl": ("radioHdmiControl", ("ON",)),
    "radioTVAudioSwitching": ("radioHdmiControl", ("ON",)),
    "radioHdmiPwOffControl": ("radioHdmiControl", ("ON",)),
    "radioPowerSaving": ("radioHdmiControl", ("ON",)),
    "radioSmartMenu": ("radioHdmiControl", ("ON",)),
}

FIELD_GATE_HINTS: Dict[str, str] = {
    "listCrossFreqAdvFr": "Available when Speaker Selection is Individual",
    "listCrossFreqAdvC": "Available when Speaker Selection is Individual",
    "listCrossFreqAdvSr": "Available when Speaker Selection is Individual",
    "listCrossFreqAdvTopMiddle": "Available when Speaker Selection is Individual",
    "listCrossFreqAll": "Available when Speaker Selection is All",
    "textMainPwOnLevel": "Available when Power On Level is set to a custom level",
    "listDialogLevelAdjust": "Turn Dialog Level Adjust On to set the level",
    "listSWLevelAdjustment": "Turn Subwoofer Level Adjust On to set the level",
    "textSWLevelAdjustment": "Turn Subwoofer Level Adjust On to set the level",
    "listRefLevelOffset": "Available when Dynamic EQ is On",
    "radioDynamicComp": "Available when Loudness Management is On",
    "radioDynComp": "Available when Loudness Management is On",
    "listDynComp": "Available when Loudness Management is On",
    "listDynamicComp": "Available when Loudness Management is On",
    "radioDynamicCompression": "Available when Loudness Management is On",
    "radioDynamicRange": "Available when Loudness Management is On",
    "radioDynamicRangeComp": "Available when Loudness Management is On",
    "radioDRC": "Available when Loudness Management is On",
    "listDynamicRange": "Available when Loudness Management is On",
    "textZone2VolLevel": "Available when ZONE2 Volume Level is custom",
    "textZone2PwOnLevel": "Available when ZONE2 Power On Level is custom",
    "textNetworkSettingIPAddress": "Available when DHCP is Off",
    "textNetworkSettingSubnetMask": "Available when DHCP is Off",
    "textNetworkSettingGateway": "Available when DHCP is Off",
    "textNetworkSettingPrimaryDNS": "Available when DHCP is Off",
    "textNetworkSettingSecondaryDNS": "Available when DHCP is Off",
    "textNetworkSettingProxyPort": "Available when Proxy is On",
    "radioHdmiStandbySrcControl": "Available when HDMI Control is On",
    "radioTVAudioSwitching": "Available when HDMI Control is On",
    "radioHdmiPwOffControl": "Available when HDMI Control is On",
    "radioPowerSaving": "Available when HDMI Control is On",
    "radioSmartMenu": "Available when HDMI Control is On",
}

# Amp Assign modes where Front Speaker page has content
FRONT_SPEAKER_AMP_MODES = frozenset({"BIA", "FRB"})


def _field_value(fields: Dict[str, Any], name: str) -> Any:
    meta = fields.get(name) or {}
    if isinstance(meta, dict):
        return meta.get("value")
    return meta


def order_fields(fields: Dict[str, Any], endpoint_id: Optional[str] = None) -> Dict[str, Any]:
    """Return a new dict with preferred order, then any leftovers."""
    if not fields:
        return {}
    preferred = list(FIELD_ORDER.get(endpoint_id or "", ()))
    out: Dict[str, Any] = {}
    for name in preferred:
        if name in fields:
            out[name] = fields[name]
    for name, meta in fields.items():
        if name not in out:
            out[name] = meta
    return out


_CROSSOVER_ROWS: Sequence[Tuple[str, str]] = (
    ("listCrossFreqAll", "All"),
    ("listCrossFreqAdvFr", "Front"),
    ("listCrossFreqAdvC", "Center"),
    ("listCrossFreqAdvSr", "Surround"),
    ("listCrossFreqAdvTopMiddle", "Top Middle"),
)

_CROSSOVER_HZ_VALUES: Sequence[str] = (
    "40Hz",
    "60Hz",
    "80Hz",
    "90Hz",
    "100Hz",
    "110Hz",
    "120Hz",
    "150Hz",
    "200Hz",
    "250Hz",
)


def _crossover_options(selected: str, template: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    vals: List[str] = []
    if template:
        for opt in template:
            if isinstance(opt, dict):
                v = str(opt.get("value") or "")
            else:
                v = str(opt)
            if v and v not in vals:
                vals.append(v)
    if not vals:
        vals = list(_CROSSOVER_HZ_VALUES)
    sel = selected if selected in vals else (vals[0] if vals else selected)
    return [
        {"value": v, "label": v, "selected": v == sel, "display": v} for v in vals
    ]


def _enrich_crossovers_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon Crossovers: always show All + Front/Center/Surround/Top Middle.

    AVR HTML only emits the active mode's <select>s; the other mode's rows are
    plain text. Synthesize missing rows as selects so order/greying match the UI.
    """
    if not fields:
        return fields

    template: Optional[List[Dict[str, Any]]] = None
    fallback = "80Hz"
    for name, _label in _CROSSOVER_ROWS:
        meta = fields.get(name)
        if not isinstance(meta, dict):
            continue
        if meta.get("type") == "select" and meta.get("options") and template is None:
            template = list(meta["options"])
    for name, _label in _CROSSOVER_ROWS:
        meta = fields.get(name)
        if isinstance(meta, dict):
            val = str(meta.get("value") or "").strip()
            if val:
                fallback = val
                break

    out: Dict[str, Any] = {}
    for name, meta in fields.items():
        if name in {n for n, _ in _CROSSOVER_ROWS}:
            continue
        out[name] = meta
        if name == "radioCrossOvers":
            for cname, clabel in _CROSSOVER_ROWS:
                existing = fields.get(cname)
                value = fallback
                if isinstance(existing, dict) and existing.get("value") not in (None, ""):
                    value = str(existing["value"])
                if (
                    isinstance(existing, dict)
                    and existing.get("type") == "select"
                    and existing.get("options")
                ):
                    row = dict(existing)
                    row.setdefault("label", clabel)
                    row.setdefault("ui_label", clabel)
                    out[cname] = row
                else:
                    opts = _crossover_options(value, template)
                    out[cname] = {
                        "type": "select",
                        "value": value,
                        "options": opts,
                        "label": clabel,
                        "ui_label": clabel,
                        "value_label": value,
                    }
    # radio missing — still append rows
    if "radioCrossOvers" not in fields:
        for cname, clabel in _CROSSOVER_ROWS:
            if cname in out:
                continue
            existing = fields.get(cname)
            value = fallback
            if isinstance(existing, dict) and existing.get("value") not in (None, ""):
                value = str(existing["value"])
            if (
                isinstance(existing, dict)
                and existing.get("type") == "select"
                and existing.get("options")
            ):
                out[cname] = existing
            else:
                out[cname] = {
                    "type": "select",
                    "value": value,
                    "options": _crossover_options(value, template),
                    "label": clabel,
                    "ui_label": clabel,
                    "value_label": value,
                }
    return out


def _enrich_eco_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon ECO page: Auto Standby heading + MAIN ZONE + grey ZONE2 label."""
    if not fields:
        return fields
    heading = {
        "type": "heading",
        "label": "Auto Standby",
        "ui_label": "Auto Standby",
        "value": "",
        "options": [],
        "inactive": False,
    }
    # Live AVR HTML omits ZONE2 Auto Standby controls; Denon still shows a grey label.
    zone2 = fields.get("radioZone2ABS") or fields.get("_zone2_auto_standby")
    if isinstance(zone2, dict):
        zone2 = dict(zone2)
        zone2.setdefault("label", "ZONE2")
        zone2.setdefault("ui_label", "ZONE2")
        zone2["inactive"] = True
        zone2["disabled"] = True
        zone2.setdefault(
            "inactive_reason",
            "Unavailable with the current ZONE2 / amp assign settings",
        )
    else:
        zone2 = {
            "type": "display",
            "label": "ZONE2",
            "ui_label": "ZONE2",
            "value": "",
            "options": [],
            "inactive": True,
            "disabled": True,
            "inactive_reason": "Unavailable with the current ZONE2 / amp assign settings",
        }

    out: Dict[str, Any] = {}
    inserted = False
    for name, meta in fields.items():
        if name in ("_heading_auto_standby", "_zone2_auto_standby", "radioZone2ABS"):
            continue
        if name == "radioMainZoneABS" and not inserted:
            out["_heading_auto_standby"] = heading
            out[name] = meta
            out["_zone2_auto_standby"] = zone2
            inserted = True
        else:
            out[name] = meta
    if not inserted:
        out["_heading_auto_standby"] = heading
        if "radioMainZoneABS" in fields:
            out["radioMainZoneABS"] = fields["radioMainZoneABS"]
        out["_zone2_auto_standby"] = zone2
    return out


def _action_button(
    label: str,
    *,
    action: Optional[str] = None,
    inactive: bool = False,
    reason: str = "",
) -> Dict[str, Any]:
    return {
        "type": "action_button",
        "label": label,
        "ui_label": label,
        "value": label,
        "options": [],
        "inactive": inactive,
        "disabled": inactive,
        "inactive_reason": reason,
        "firmware_action": action,
    }


def _enrich_firmware_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon Firmware page: Update / Notifications / Add Feature / Web Update."""
    skip = {
        "setbtnUpdateCheck",
        "setbtnAddNewFeature",
        "setbtnFirmwareUpdate",
        "setUpdateCheck",
        "setAddNewFeature",
        "setFirmwareUpdateWebUpdate",
        "setFirmwareUpdate",
        "_heading_fw_update",
        "_btn_fw_update",
        "_heading_fw_notifications",
        "_heading_fw_add_feature",
        "_btn_fw_add_feature",
        "_heading_fw_web_update",
        "_btn_fw_web_update",
        "_heading_fw_local",
        "_fw_local_upload",
    }
    out: Dict[str, Any] = {
        "_heading_fw_update": {
            "type": "heading",
            "label": "Update",
            "ui_label": "Update",
            "value": "",
            "options": [],
            "inactive": False,
        },
        "_btn_fw_update": _action_button("Update", action="update"),
        "_heading_fw_notifications": {
            "type": "heading",
            "label": "Notifications",
            "ui_label": "Notifications",
            "value": "",
            "options": [],
            "inactive": False,
        },
    }
    for name in ("radioUpdateNotification", "radioUpgradeNotification"):
        if name in fields and isinstance(fields[name], dict):
            meta = dict(fields[name])
            # Ensure On/Off options always exist even if AVR HTML was sparse.
            opts = meta.get("options")
            if not isinstance(opts, list) or len(opts) < 2:
                meta["options"] = [
                    {"value": "ON", "label": "On", "selected": str(meta.get("value")) == "ON"},
                    {"value": "OFF", "label": "Off", "selected": str(meta.get("value")) == "OFF"},
                ]
            else:
                for opt in opts:
                    if isinstance(opt, dict):
                        opt["selected"] = str(opt.get("value")) == str(meta.get("value") or "")
            out[name] = meta
        else:
            out[name] = {
                "type": "radio",
                "value": None,
                "options": [
                    {"value": "ON", "label": "On", "selected": False},
                    {"value": "OFF", "label": "Off", "selected": False},
                ],
                "ui_label": (
                    "Update" if name == "radioUpdateNotification" else "Upgrade"
                ),
            }
    out["_heading_fw_add_feature"] = {
        "type": "heading",
        "label": "Add New Feature",
        "ui_label": "Add New Feature",
        "value": "",
        "options": [],
        "inactive": False,
    }
    out["_btn_fw_add_feature"] = _action_button(
        "Add New Feature", action="add_new_feature"
    )
    out["_heading_fw_web_update"] = {
        "type": "heading",
        "label": "Web Update",
        "ui_label": "Web Update",
        "value": "",
        "options": [],
        "inactive": False,
    }
    out["_btn_fw_web_update"] = _action_button("Web Update", action="web_update")
    out["_heading_fw_local"] = {
        "type": "heading",
        "label": "Local Firmware Upload",
        "ui_label": "Local Firmware Upload",
        "value": "",
        "options": [],
        "inactive": False,
    }
    out["_fw_local_upload"] = {
        "type": "firmware_upload",
        "label": "Upload",
        "ui_label": "Upload",
        "value": "",
        "options": [],
        "inactive": False,
        "disabled": False,
        "inactive_reason": (
            "Official Denon AVR-X1200W package only. Wrong files can brick the unit. "
            "If the AVR is not in upload mode, Web Update is started first."
        ),
        "upload_path": "/api/firmware/local-upload",
        "status_path": "/api/firmware/local-upload/status",
    }
    for name, meta in fields.items():
        if name in skip or name in out:
            continue
        if str(meta.get("type") if isinstance(meta, dict) else "") in (
            "hidden",
            "button",
            "submit",
        ):
            continue
        out[name] = meta
    return out


def _enrich_network_settings_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(fields)
    for name in (
        "buttonNetworkSettingDHCPSet",
        "buttonNetworkSettingProxySet",
        "buttonNetworkSettingTestConnection",
        "radioNetworkSettingDHCP_OnOff",
        "hiddenNetworkSettingProxy_OnOff",
        "hiddenNetworkSettingDHCP_OnOff",
    ):
        out.pop(name, None)
    # Re-run inference after strip — disabled IP/port flags are still present.
    from .denon_client import _infer_missing_radio_values

    _infer_missing_radio_values(out)
    # Denon Proxy radios: always expose Off / On(Address) / On(Name).
    proxy = out.get("radioNetworkSettingProxy_OnOff")
    if isinstance(proxy, dict):
        opts = proxy.get("options")
        if not isinstance(opts, list) or len(opts) < 3:
            cur = str(proxy.get("value") or "")
            proxy["options"] = [
                {"value": "OFF", "label": "Off", "selected": cur.upper() == "OFF"},
                {
                    "value": "ADR",
                    "label": "On(Address)",
                    "selected": cur.upper() == "ADR",
                },
                {
                    "value": "NAM",
                    "label": "On(Name)",
                    "selected": cur.upper() == "NAM",
                },
            ]
            out["radioNetworkSettingProxy_OnOff"] = proxy
    for name in ("radioNetworkSettingDHCP", "radioNetworkSettingProxy_OnOff"):
        meta = out.get(name)
        if not isinstance(meta, dict):
            continue
        opts = meta.get("options")
        if isinstance(opts, list):
            cur = str(meta.get("value") or "").upper()
            for opt in opts:
                if isinstance(opt, dict):
                    opt["selected"] = str(opt.get("value") or "").upper() == cur
    out["_btn_network_settings_save"] = {
        "type": "network_save",
        "label": "Save",
        "ui_label": "Save",
        "value": "Save",
        "options": [],
        "inactive": False,
        "network_save_kind": "settings",
    }
    out["_note_network_settings"] = {
        "type": "display",
        "label": "Note",
        "ui_label": "Note",
        "value": (
            "The network connection will reset if you change and save any network "
            "setting. Please wait 60 seconds then reload this web page."
        ),
        "options": [],
        "inactive": False,
    }
    return out


def _enrich_network_connection_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(fields)
    out.pop("buttonNetworkSettingTestConnection", None)
    # Denon shows Connect Using as static text (Wireless / Wired)
    wifi = ""
    meta = fields.get("radioWifi") or {}
    if isinstance(meta, dict):
        wifi = str(meta.get("value") or "").upper()
    connect_using = "Wireless (Wi-Fi)" if wifi == "ON" else "Wired"
    out["_display_connect_using"] = {
        "type": "display",
        "label": "Connect Using",
        "ui_label": "Connect Using",
        "value": connect_using,
        "options": [],
        "inactive": False,
    }
    out["_btn_network_connect"] = {
        "type": "network_save",
        "label": "Connect",
        "ui_label": "Connect",
        "value": "Connect",
        "options": [],
        "inactive": False,
        "network_save_kind": "connect",
    }
    return out


def apply_field_gates(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Mark inactive fields (grey-out). Does not remove them."""
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if not isinstance(meta, dict):
            out[name] = meta
            continue
        m = dict(meta)
        if m.get("type") in (
            "heading",
            "display",
            "action_button",
            "subheading",
            "firmware_upload",
            "network_save",
            "note",
        ):
            # Preserve explicit inactive on synthetic display rows
            if "inactive" not in m:
                m["inactive"] = False
            out[name] = m
            continue
        gate = FIELD_GATES.get(name)
        inactive = bool(m.get("disabled"))
        hint = None
        if inactive:
            hint = "Unavailable with the current settings on the AVR"
        if gate:
            parent, allowed = gate
            if parent in fields:
                current = str(_field_value(fields, parent) or "")
                allowed_norm = {str(a) for a in allowed}
                if current not in allowed_norm:
                    inactive = True
                    hint = FIELD_GATE_HINTS.get(name) or hint
        m["inactive"] = inactive
        if hint and inactive:
            m["inactive_reason"] = hint
        elif not inactive:
            m.pop("inactive_reason", None)
        # Network IP fields: Denon marks disabled when DHCP On — clear disabled so
        # our gate can re-enable them when user selects DHCP Off locally.
        if name.startswith("textNetworkSetting") and not inactive:
            m["disabled"] = False
        out[name] = m
    return out


def _form_action_button(label: str, post_fields: Dict[str, str]) -> Dict[str, Any]:
    return {
        "type": "action_button",
        "label": label,
        "ui_label": label,
        "value": label,
        "options": [],
        "inactive": False,
        "form_post_fields": post_fields,
    }


def _enrich_source_rename_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon: Set Defaults (top) + rename texts + Set (bottom)."""
    out: Dict[str, Any] = {
        "_btn_rename_defaults": _form_action_button(
            "Set Defaults", {"setFuncRenameDefault": "Set Defaults"}
        ),
    }
    for name, meta in (fields or {}).items():
        if name.startswith("set") or name in (
            "setFuncRenameDefault",
            "setFuncRenameAll",
            "setFuncRenameBD",
            "setFuncRenameMPLAY",
        ):
            continue
        if name.startswith("setbtn") or name.startswith("_btn_"):
            continue
        out[name] = meta
    out["_btn_rename_set"] = _form_action_button(
        "Set", {"setFuncRenameAll": "on"}
    )
    return out


def _enrich_hide_sources_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon: standard sources, network note, network sources, Set Network."""
    skip = {"buttonNet", "setPureDirectOn", "setSetupLock", "_note_hide_network",
            "_display_bluray_zone", "_btn_set_network_contents"}
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in skip or name.startswith("set"):
            continue
        out[name] = meta

    # Blu-ray is fixed to MAIN ZONE on this amp assign (no Show/Hide radios).
    ordered: Dict[str, Any] = {}
    for name, meta in out.items():
        ordered[name] = meta
        if name == "DVD" and "_display_bluray_zone" not in ordered:
            ordered["_display_bluray_zone"] = {
                "type": "display",
                "label": "Blu-ray",
                "ui_label": "Blu-ray",
                "value": "MAIN ZONE",
                "options": [],
                "inactive": False,
            }
    if "_display_bluray_zone" not in ordered:
        ordered["_display_bluray_zone"] = {
            "type": "display",
            "label": "Blu-ray",
            "ui_label": "Blu-ray",
            "value": "MAIN ZONE",
            "options": [],
            "inactive": False,
        }

    # Insert note before first network source
    final: Dict[str, Any] = {}
    note = {
        "type": "note",
        "label": "Note",
        "ui_label": "Note",
        "value": (
            "The network connection will reset if you change this setting for any "
            "of the network sources listed below. Please wait 60 seconds then "
            "reload this web page."
        ),
        "options": [],
        "inactive": False,
    }
    inserted = False
    for name, meta in ordered.items():
        if name in ("FAVORITES", "IRADIO", "SERVER") and not inserted:
            final["_note_hide_network"] = note
            inserted = True
        final[name] = meta
    if not inserted:
        final["_note_hide_network"] = note
    final["_btn_set_network_contents"] = _form_action_button(
        "Set Network contents", {"buttonNet": "on"}
    )
    return final


def _enrich_source_level_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon: Source Level text + Set button (explicit apply)."""
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in ("setSourceLevelDigital", "setbtnInFuncLev") or name.startswith(
            "setbtn"
        ):
            continue
        if name == "textSourceLevelDigital" and isinstance(meta, dict):
            m = dict(meta)
            m.setdefault("label", "Source Level")
            m.setdefault("ui_label", "Source Level")
            m["unit"] = "dB"
            m["explicit_set"] = True
            out[name] = m
        else:
            out[name] = meta
    out["_btn_source_level_set"] = _form_action_button(
        "Set", {"setSourceLevelDigital": "on"}
    )
    return out


def _enrich_levels_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon Speakers/Levels: sliders preview locally; Set pushes setCLA."""
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in ("setCLA", "setbtnCLA") or name.startswith("setbtn"):
            continue
        if isinstance(meta, dict) and (
            name.startswith("textCV") or meta.get("type") == "range"
        ):
            m = dict(meta)
            m["unit"] = m.get("unit") or "dB"
            m["explicit_set"] = True
            out[name] = m
        else:
            out[name] = meta
    out["_btn_levels_set"] = _form_action_button("Set", {"setCLA": "Set"})
    return out


def _enrich_surround_parameter_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Cinema EQ → Loudness → Dynamic Compression (when On) → LFE + Set."""
    dyn_names = (
        "radioDynamicComp",
        "radioDynComp",
        "listDynComp",
        "listDynamicComp",
        "radioDynamicCompression",
        "radioDynamicRange",
        "radioDynamicRangeComp",
        "radioDRC",
        "listDynamicRange",
    )
    dyn_field = None
    dyn_meta = None
    for name in dyn_names:
        meta = (fields or {}).get(name)
        if isinstance(meta, dict):
            dyn_field = name
            dyn_meta = dict(meta)
            dyn_meta["label"] = "Dynamic Compression"
            dyn_meta["ui_label"] = "Dynamic Compression"
            break

    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in dyn_names or name in ("setLfeLevel",) or name.startswith("setbtn"):
            continue
        if name == "radioLoudnessManagement":
            out[name] = meta
            if dyn_field and dyn_meta is not None:
                out[dyn_field] = dyn_meta
        elif name == "textLfeLevel" and isinstance(meta, dict):
            m = dict(meta)
            m["label"] = "Low Frequency Effects"
            m["ui_label"] = "Low Frequency Effects"
            m["unit"] = "dB"
            m["explicit_set"] = True
            out[name] = m
            out["_btn_lfe_set"] = _form_action_button("Set", {"setLfeLevel": "on"})
        else:
            out[name] = meta

    # Loudness missing from page (no Dolby signal) — still attach dyn if present
    if dyn_field and dyn_meta is not None and dyn_field not in out:
        rebuilt: Dict[str, Any] = {}
        inserted = False
        for name, meta in out.items():
            if name == "textLfeLevel" and not inserted:
                rebuilt[dyn_field] = dyn_meta
                inserted = True
            rebuilt[name] = meta
        if not inserted:
            rebuilt[dyn_field] = dyn_meta
        out = rebuilt

    if "textLfeLevel" in (fields or {}) and "_btn_lfe_set" not in out:
        out["_btn_lfe_set"] = _form_action_button("Set", {"setLfeLevel": "on"})
    return out


def _enrich_audio_delay_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in ("setAudioDelay",) or name.startswith("setbtn"):
            continue
        if name == "textAudioDelay" and isinstance(meta, dict):
            m = dict(meta)
            m["label"] = "Audio Delay"
            m["ui_label"] = "Audio Delay"
            m["unit"] = "ms"
            m["explicit_set"] = True
            out[name] = m
        else:
            out[name] = meta
    out["_btn_audio_delay_set"] = _form_action_button("Set", {"setAudioDelay": "on"})
    return out


def _enrich_volume_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Power On Level custom dB + Set (when Level selected)."""
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in ("setMainPwOnLevel",) or name.startswith("setbtn"):
            continue
        if name == "textMainPwOnLevel" and isinstance(meta, dict):
            m = dict(meta)
            m["label"] = "Level"
            m["ui_label"] = "Level"
            m["unit"] = "dB"
            m["explicit_set"] = True
            out[name] = m
            out["_btn_pw_on_level_set"] = _form_action_button(
                "Set", {"setMainPwOnLevel": "on"}
            )
        else:
            out[name] = meta
    if "textMainPwOnLevel" in (fields or {}) and "_btn_pw_on_level_set" not in out:
        out["_btn_pw_on_level_set"] = _form_action_button(
            "Set", {"setMainPwOnLevel": "on"}
        )
    return out


def _enrich_distances_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon Speakers/Distances: unit text fields + Set."""
    mode = str((fields or {}).get("radioDelayTimeMode", {}).get("value") or "F")
    unit = "ft" if mode.upper() == "F" else "m"
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in ("setDelayTimeAllSet",) or name.startswith("setbtn"):
            continue
        if name.startswith("textDelayTime") and isinstance(meta, dict):
            m = dict(meta)
            m["unit"] = unit
            m["explicit_set"] = True
            out[name] = m
        else:
            out[name] = meta
    out["_btn_distances_set"] = _form_action_button(
        "Set", {"setDelayTimeAllSet": "Set"}
    )
    return out


def _enrich_friendly_name_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon Network/Friendly Name: template, edit name + Set, Set Defaults."""
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in ("FriendlySet", "FriendlyDef", "FriendlyErrMsg") or name.startswith(
            ("setBtn", "defBtn")
        ):
            continue
        if name == "Friendlyname" and isinstance(meta, dict):
            m = dict(meta)
            m["label"] = "Edit Name"
            m["ui_label"] = "Edit Name"
            m["explicit_set"] = True
            out[name] = m
            out["_btn_friendly_set"] = _form_action_button(
                "Set", {"FriendlySet": "Set"}
            )
        else:
            out[name] = meta
    out["_btn_friendly_defaults"] = _form_action_button(
        "Set Defaults", {"FriendlyDef": "Def"}
    )
    return out


def _enrich_zone_rename_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon General/Zone Rename: Set Defaults (top) + names + Set."""
    out: Dict[str, Any] = {
        "_btn_zone_rename_defaults": _form_action_button(
            "Set Defaults", {"setZoneRenameDefault": "on"}
        ),
    }
    for name, meta in (fields or {}).items():
        if (
            name.startswith("set")
            or name.startswith("setbtn")
            or name.startswith("_btn_")
        ):
            continue
        if name.startswith("textZoneRename") and isinstance(meta, dict):
            m = dict(meta)
            m["explicit_set"] = True
            out[name] = m
        else:
            out[name] = meta
    out["_btn_zone_rename_set"] = _form_action_button(
        "Set", {"setZoneRenameAll": "on"}
    )
    return out


def _enrich_quick_select_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon General/Quick Select Names: Set Defaults + names + Set."""
    out: Dict[str, Any] = {
        "_btn_quick_select_defaults": _form_action_button(
            "Set Defaults",
            {"setBtnQuickSelectNameDefault": "Set Defaults"},
        ),
    }
    for name, meta in (fields or {}).items():
        if (
            name.startswith("set")
            or name.startswith("setbtn")
            or name.startswith("_btn_")
        ):
            continue
        if name.startswith("textQuickSelectName") and isinstance(meta, dict):
            m = dict(meta)
            m["explicit_set"] = True
            out[name] = m
        else:
            out[name] = meta
    out["_btn_quick_select_set"] = _form_action_button(
        "Set", {"setQuickSelectNameAll": "on"}
    )
    return out


def _enrich_audyssey_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure -Reference Level Offset sits under Dynamic EQ (gated On)."""
    ref = fields.get("listRefLevelOffset") if isinstance(fields, dict) else None
    if isinstance(ref, dict) and ref.get("options"):
        ref_row = dict(ref)
    else:
        ref_row = {
            "type": "radio",
            "value": (ref or {}).get("value") if isinstance(ref, dict) else "0dB",
            "options": [
                {"value": "0dB", "label": "0dB", "selected": True, "display": "0dB"},
                {"value": "5dB", "label": "5dB", "selected": False, "display": "5dB"},
                {"value": "10dB", "label": "10dB", "selected": False, "display": "10dB"},
                {"value": "15dB", "label": "15dB", "selected": False, "display": "15dB"},
            ],
        }
        if isinstance(ref, dict) and ref.get("value"):
            val = str(ref["value"])
            ref_row["value"] = val
            for opt in ref_row["options"]:
                opt["selected"] = opt["value"] == val
    ref_row["label"] = "Reference Level Offset"
    ref_row["ui_label"] = "Reference Level Offset"
    ref_row["indent"] = True

    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name == "listRefLevelOffset":
            continue
        out[name] = meta
        if name == "radioDynamicEq":
            out["listRefLevelOffset"] = ref_row
    if "listRefLevelOffset" not in out:
        out["listRefLevelOffset"] = ref_row
    return out


def _enrich_subwoofer_level_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """When Adjust is Off, Denon shows Subwoofer Level as static text."""
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name.startswith("_display_"):
            continue
        out[name] = meta
    has_editable = any(
        n in out for n in ("listSWLevelAdjustment", "textSWLevelAdjustment")
    )
    display = fields.get("_display_sw_level") if isinstance(fields, dict) else None
    if not has_editable:
        val = "+ 5.0 dB"
        if isinstance(display, dict) and display.get("value"):
            val = str(display["value"])
        out["_display_sw_level"] = {
            "type": "display",
            "label": "Subwoofer Level",
            "ui_label": "Subwoofer Level",
            "value": val,
            "options": [],
            "inactive": False,
        }
    return out


def _enrich_tv_format_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon TV Format: Format radios + network-reset note."""
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name.startswith("set") and name not in ("radioGuiFormat",):
            continue
        if name == "radioGuiFormat" and isinstance(meta, dict):
            m = dict(meta)
            m["label"] = "Format"
            m["ui_label"] = "Format"
            out[name] = m
        elif not name.startswith("_"):
            out[name] = meta
    out["_note_tv_format"] = {
        "type": "note",
        "label": "Note",
        "ui_label": "Note",
        "value": (
            "The network connection will reset if you change the video format. "
            "Please wait 60 seconds then reload this web page."
        ),
        "options": [],
        "inactive": False,
        "note_style": "plain",
    }
    return out


def _hdmi_display(label: str, value: str, *, indent: bool = False) -> Dict[str, Any]:
    return {
        "type": "display",
        "label": label,
        "ui_label": label,
        "value": value,
        "options": [],
        "inactive": False,
        "indent": indent,
    }


def _enrich_hdmi_setup_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Match Denon HDMI Setup: Audio Out / ARC / Pass Through status + indented children."""
    audio = "AVR"
    arc = "On"
    passthrough = "On"
    for name, meta in (fields or {}).items():
        if not isinstance(meta, dict):
            continue
        if name == "_display_hdmi_audio_out" and meta.get("value"):
            audio = str(meta["value"])
        elif name == "_display_hdmi_arc" and meta.get("value"):
            arc = str(meta["value"])
        elif name == "_display_hdmi_pass" and meta.get("value"):
            passthrough = str(meta["value"])

    child_labels = {
        "radioHdmiStandbySrcControl": "Pass Through Source",
        "radioTVAudioSwitching": "TV Audio Switching",
        "radioHdmiPwOffControl": "Power Off Control",
        "radioPowerSaving": "Power Saving",
        "radioSmartMenu": "Smart Menu",
    }

    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name.startswith("_display_hdmi_") or name.startswith("_note_"):
            continue
        if name.startswith("set") and not name.startswith("radio"):
            continue
        if name == "radioAutoLipSync":
            out[name] = meta
            out["_display_hdmi_audio_out"] = _hdmi_display("HDMI Audio Out", audio)
        elif name == "radioHdmiControl":
            out[name] = meta
            out["_display_hdmi_arc"] = _hdmi_display("ARC", arc, indent=True)
            out["_display_hdmi_pass"] = _hdmi_display(
                "HDMI Pass Through", passthrough, indent=True
            )
        elif name in child_labels and isinstance(meta, dict):
            m = dict(meta)
            m["label"] = child_labels[name]
            m["ui_label"] = child_labels[name]
            m["indent"] = True
            if name == "radioHdmiStandbySrcControl":
                m["layout"] = "vertical"
            out[name] = m
        else:
            out[name] = meta

    if "radioAutoLipSync" not in out and "radioAutoLipSync" in (fields or {}):
        out = {"radioAutoLipSync": fields["radioAutoLipSync"], **out}
    if "_display_hdmi_audio_out" not in out:
        # Ensure Audio Out appears even if Auto Lip Sync missing
        rebuilt: Dict[str, Any] = {}
        inserted = False
        for name, meta in out.items():
            rebuilt[name] = meta
            if name == "radioAutoLipSync":
                rebuilt["_display_hdmi_audio_out"] = _hdmi_display("HDMI Audio Out", audio)
                inserted = True
        if not inserted:
            rebuilt = {
                "_display_hdmi_audio_out": _hdmi_display("HDMI Audio Out", audio),
                **rebuilt,
            }
        out = rebuilt
    if "_display_hdmi_arc" not in out:
        rebuilt = {}
        for name, meta in out.items():
            rebuilt[name] = meta
            if name == "radioHdmiControl":
                rebuilt["_display_hdmi_arc"] = _hdmi_display("ARC", arc, indent=True)
                rebuilt["_display_hdmi_pass"] = _hdmi_display(
                    "HDMI Pass Through", passthrough, indent=True
                )
        out = rebuilt
    return out


# Internal Denon form bookkeeping — always forced on write; never useful to clients.
_INTERNAL_FIELD_NAMES = frozenset(
    {
        "setPureDirectOn",
        "setSetupLock",
    }
)
_INTERNAL_FIELD_TYPES = frozenset({"hidden", "button", "submit"})


def strip_internal_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Drop AVR bookkeeping / raw button fields from API state responses.

    Writes still inject ``setPureDirectOn`` / ``setSetupLock`` via safety.
    Explicit Set actions use ``action_button`` rows (``_btn_*``), not ``setbtn*``.
    """
    out: Dict[str, Any] = {}
    for name, meta in (fields or {}).items():
        if name in _INTERNAL_FIELD_NAMES:
            continue
        if name.lower().startswith("setbtn"):
            continue
        if isinstance(meta, dict) and meta.get("type") in _INTERNAL_FIELD_TYPES:
            continue
        out[name] = meta
    return out


def layout_fields(
    fields: Dict[str, Any], endpoint_id: Optional[str] = None
) -> Dict[str, Any]:
    laid = order_fields(fields, endpoint_id)
    if endpoint_id == "speakers_crossovers_s_speakersetup":
        laid = _enrich_crossovers_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "general_eco_s_general":
        laid = _enrich_eco_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "general_firmware_s_firmware":
        laid = _enrich_firmware_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "network_settings_s_network_setting_dhcp":
        laid = _enrich_network_settings_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "network_connection_s_network_setting_dhcp":
        laid = _enrich_network_connection_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "inputs_sourcerename_s_rename":
        laid = _enrich_source_rename_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "inputs_hidesources_s_delete":
        laid = _enrich_hide_sources_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "inputs_sourcelevel_s_inputsetup":
        laid = _enrich_source_level_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "speakers_levels_s_speakersetup":
        laid = _enrich_levels_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "speakers_distances_s_speakersetup":
        laid = _enrich_distances_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "network_friendlyname_s_network":
        laid = _enrich_friendly_name_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "general_zonerename_s_general":
        laid = _enrich_zone_rename_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "general_selectnames_s_general":
        laid = _enrich_quick_select_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "audio_surroundparameter_s_audio":
        laid = _enrich_surround_parameter_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "audio_audiodelay_s_audio":
        laid = _enrich_audio_delay_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "audio_volume_s_audio":
        laid = _enrich_volume_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "audio_audyssey_s_audio":
        laid = _enrich_audyssey_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "audio_subwooferlevel_s_audio":
        laid = _enrich_subwoofer_level_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "video_tvformat_s_video":
        laid = _enrich_tv_format_fields(laid)
        laid = order_fields(laid, endpoint_id)
    elif endpoint_id == "video_hdmisetup_s_video":
        laid = _enrich_hdmi_setup_fields(laid)
        laid = order_fields(laid, endpoint_id)
    return strip_internal_fields(apply_field_gates(laid))


def menu_inactive_flags(context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return menu node id → {inactive, reason} from live AVR context."""
    amp = str(context.get("amp_assign") or "")
    flags: Dict[str, Dict[str, Any]] = {}
    if amp and amp not in FRONT_SPEAKER_AMP_MODES:
        flags["speakers_front"] = {
            "inactive": True,
            "inactive_reason": "Available when Amp Assign is Bi-Amp or Front B",
        }
    return flags
