"""Safety policy for Denon X1200W Setup API.

Blocks destructive / lock-out operations. Read-only access remains for info pages.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Set

# Endpoint ids that must never accept POST
WRITE_BLOCKED_ENDPOINT_IDS: Set[str] = {
    # Firmware *update* pages stay blocked; main firmware form unlocked for notifications only
    "general_firmware_r_firmware",
    # Legacy Setup Lock alias — use general_setuplock_s_general only (unlocked)
    "18_others_s_otherssetuplock",
    # Legacy network read aliases (writes go through s_ endpoints below)
    "network_settings_r_network_setting_dhcp",
    "network_connection_r_network_setting_dhcp",
    # Audyssey Setup mic wizard — engage stub only; never post Start/Begin Test
    "speakers_audyssey_setup",
}

# Explicitly unlocked critical endpoints (must not match broader blocks below).
WRITE_UNLOCKED_ENDPOINT_IDS: Set[str] = {
    # Approved: Setup Lock On/Off (Denon: Lock remains reachable when locked)
    "general_setuplock_s_general",
    # Approved: Firmware form — notifications + Update / Add New Feature / Web Update actions
    "general_firmware_s_firmware",
    # Approved: Information → Notification Alerts On/Off
    "general_information_s_information",
    # Approved: Network Settings + Connection (can disconnect — UI requires explicit Save)
    "network_settings_s_network_setting_dhcp",
    "network_connection_s_network_setting_dhcp",
}

# Network fields allowed only when posting to unlocked network endpoints
NETWORK_WRITE_FIELDS: Set[str] = {
    "buttonNetworkSettingDHCPSet",
    "buttonNetworkSettingProxySet",
    "buttonNetworkSettingTestConnection",
    "radioNetworkSettingDHCP",
    "radioNetworkSettingDHCP_OnOff",
    "radioNetworkSettingProxy_OnOff",
    "hiddenNetworkSettingProxy_OnOff",
    "hiddenNetworkSettingDHCP_OnOff",
    "textNetworkSettingIPAddress",
    "textNetworkSettingSubnetMask",
    "textNetworkSettingGateway",
    "textNetworkSettingPrimaryDNS",
    "textNetworkSettingSecondaryDNS",
    "textNetworkSettingProxyPort",
    "radioWifi",
    "listWifi_WifiSetupHow",
}

# Wizard / maintenance paths never accepted as POST targets
WRITE_BLOCKED_WIZARD_SUBSTRINGS = (
    "audysseysetup",
    "audyssey_setup",
    "begintest",
    "begin_test",
    "spcalibration",
    "setupassistant",
    "beginsetup",
    "maintenance",
)

# Substrings — if endpoint id or submit URL contains these, treat as write-blocked
# (skipped when endpoint is in WRITE_UNLOCKED_ENDPOINT_IDS)
WRITE_BLOCKED_ID_SUBSTRINGS = (
    "firmware",
    "setuplock",  # still blocks 18_others; unlocked id is allowlisted above
    "config_save",
    "config_load",
    "/save/",
    "/load/",
)

WRITE_BLOCKED_URL_SUBSTRINGS = (
    "/SAVE/",
    "/LOAD/",
    "f_config_save",
    "f_config_load",
    "s_firmwareupdate",  # DPMS path — not exposed on X1200W Firmware UI
    # formPostHandler unlocked only via /api/firmware/local-upload (multipart + confirm)
)

# Fields that must never be written (stripped from every POST)
WRITE_BLOCKED_FIELDS: Set[str] = {
    "setFirmwareUpdateWebUpdate",
    "setFirmwareUpdate",
    "setUpdateCheck",
    "setAddNewFeature",
    "setbtnFirmwareUpdate",
    "setbtnUpdateCheck",
    "setbtnAddNewFeature",
    # radioSetupLock allowed — Setup Lock page (unlocked with permission)
    "setSetupLock",  # hidden flag on other forms — always forced OFF below
    "appFirmware",
    "appFirmwareFile",
    "buttonNetworkSettingDHCPSet",
    "buttonNetworkSettingProxySet",
    "buttonNetworkSettingTestConnection",
    "radioNetworkSettingDHCP",
    "radioNetworkSettingDHCP_OnOff",
    "radioNetworkSettingProxy_OnOff",
    "hiddenNetworkSettingProxy_OnOff",
    "hiddenNetworkSettingDHCP_OnOff",
    "textNetworkSettingIPAddress",
    "textNetworkSettingSubnetMask",
    "textNetworkSettingGateway",
    "textNetworkSettingPrimaryDNS",
    "textNetworkSettingSecondaryDNS",
    "textNetworkSettingProxyPort",
}

# Hidden status fields we force to safe constants on every submit merge
SAFE_FORCED_FIELDS: Dict[str, str] = {
    "setPureDirectOn": "OFF",
    "setSetupLock": "OFF",
}


def is_write_blocked(endpoint_id: str, submit_url: str = "") -> Optional[str]:
    eid = (endpoint_id or "").lower()
    url = (submit_url or "").lower()
    if eid in {x.lower() for x in WRITE_UNLOCKED_ENDPOINT_IDS}:
        return None
    if eid in WRITE_BLOCKED_ENDPOINT_IDS:
        return f"Writes blocked for critical endpoint '{endpoint_id}'"
    for part in WRITE_BLOCKED_ID_SUBSTRINGS:
        if part in eid:
            return f"Writes blocked: endpoint id contains '{part}'"
    for part in WRITE_BLOCKED_URL_SUBSTRINGS:
        if part.lower() in url:
            return f"Writes blocked: URL matches critical path '{part}'"
    for part in WRITE_BLOCKED_WIZARD_SUBSTRINGS:
        if part in eid or part in url:
            return (
                f"Wizard/service path blocked ('{part}'). "
                "Audyssey Setup engage is stub-only and never starts the mic wizard."
            )
    return None


def sanitize_write_fields(
    fields: Dict[str, str], *, endpoint_id: Optional[str] = None
) -> Dict[str, str]:
    """Strip blocked fields and force safe hidden defaults."""
    eid = (endpoint_id or "").lower()
    unlocked = eid in {x.lower() for x in WRITE_UNLOCKED_ENDPOINT_IDS}
    cleaned = {
        k: v
        for k, v in fields.items()
        if k not in WRITE_BLOCKED_FIELDS and not k.lower().startswith("setbtn")
    }
    cleaned.update(SAFE_FORCED_FIELDS)
    if unlocked and "radioSetupLock" in fields:
        cleaned["radioSetupLock"] = str(fields["radioSetupLock"])
    # Firmware: allow notification radios; keep update action flags forced off
    if unlocked and eid == "general_firmware_s_firmware":
        for name in ("radioUpdateNotification", "radioUpgradeNotification"):
            if name in fields:
                cleaned[name] = str(fields[name])
        for name in (
            "setUpdateCheck",
            "setAddNewFeature",
            "setFirmwareUpdateWebUpdate",
            "setFirmwareUpdate",
        ):
            cleaned[name] = "off"
    if unlocked and eid == "general_information_s_information":
        if "radioAlerts" in fields:
            cleaned["radioAlerts"] = str(fields["radioAlerts"])
    if unlocked and eid in {
        "network_settings_s_network_setting_dhcp",
        "network_connection_s_network_setting_dhcp",
    }:
        for name in NETWORK_WRITE_FIELDS:
            if name in fields:
                cleaned[name] = str(fields[name])
    return cleaned


def annotate_catalog_item(item: Dict) -> Dict:
    """Add write_allowed / write_block_reason to a catalog entry."""
    reason = is_write_blocked(item.get("id", ""), item.get("submit_url", ""))
    out = dict(item)
    out["write_allowed"] = reason is None
    out["write_block_reason"] = reason
    out["read_allowed"] = True
    return out


def catalog_filter_writable_only(items: Iterable[Dict], writable_only: bool) -> list:
    out = [annotate_catalog_item(i) for i in items]
    if writable_only:
        out = [i for i in out if i["write_allowed"]]
    return out
