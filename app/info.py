"""Read-only info extractors (firmware version, network settings)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .denon_client import DenonSetupClient

try:
    from .field_labels import clean_display_text
except ImportError:  # pragma: no cover
    def clean_display_text(value):  # type: ignore
        return str(value or "").strip()

INFO_FIRMWARE_URL = "/SETUP/GENERAL/INFORMATION/d_information.asp"
FIRMWARE_PAGE_URL = "/SETUP/GENERAL/FIRMWARE/d_firmware.asp"
NETWORK_SETTINGS_URL = "/SETUP/NETWORK/SETTINGS/d_network_setting_dhcp.asp"
NETWORK_CONNECTION_URL = "/SETUP/NETWORK/CONNECTION/d_network_setting_dhcp.asp"
NETWORK_FRIENDLY_URL = "/SETUP/NETWORK/FRIENDLYNAME/d_network.asp"
NETWORK_CONTROL_URL = "/SETUP/NETWORK/IPCONTROL/d_network.asp"

PROTOCOL_DIR = Path(__file__).resolve().parents[1] / "protocol"


def _row_pairs(html: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for m in re.finditer(
        r"<TD[^>]*>\s*(?:<b>)?\s*(?:&nbsp;|\s)*-?\s*([^<]+?)\s*(?:</b>)?\s*</TD>\s*"
        r"<TD[^>]*>\s*(.*?)\s*</TD>",
        html,
        re.I | re.S,
    ):
        label = re.sub(r"\s+", " ", m.group(1)).strip(" \t\r\n\u00a0-")
        raw_val = m.group(2)
        if re.search(r"<input\b", raw_val, re.I):
            vm = re.search(r"""value\s*=\s*['"]([^'"]*)['"]""", raw_val, re.I)
            # Also capture checked radio nearby by looking at whole cell siblings later
            value = vm.group(1).strip() if vm else ""
            # radio group: prefer checked option's value
            radios = list(
                re.finditer(
                    r"""<input\b([^>]*type=['"]radio['"][^>]*)>""",
                    raw_val,
                    re.I,
                )
            )
            if radios:
                chosen = None
                for rm in radios:
                    attrs = rm.group(1)
                    if re.search(r"\bchecked\b", attrs, re.I):
                        vm2 = re.search(
                            r"""value\s*=\s*['"]([^'"]*)['"]""", attrs, re.I
                        )
                        if vm2:
                            chosen = vm2.group(1)
                            break
                if chosen is not None:
                    value = chosen
        else:
            value = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw_val)).strip()
        if label:
            pairs.append((label, value))
    return pairs


def _facts_dict(html: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for label, value in _row_pairs(html):
        if value != "":
            out[label] = value
        elif label not in out:
            out[label] = value
    return out


def _normalize_ip_like(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return s
    # Denon often zero-pads octets: 192.168.020.050 -> 192.168.20.50
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", s):
        return ".".join(str(int(p)) for p in s.split("."))
    if re.fullmatch(r"\d+", s) and len(s) <= 5:
        # ports like 00080
        return str(int(s))
    return s


def _field_value(fields: Dict[str, Any], name: str) -> Optional[str]:
    meta = fields.get(name) or {}
    v = meta.get("value")
    if v is None:
        return None
    return _normalize_ip_like(str(v)) if any(
        k in name.lower() for k in ("ip", "gateway", "dns", "mask", "port")
    ) else str(v)


def _norm_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", label.lower())


def _pick_fact(facts: Dict[str, str], *names: str) -> Optional[str]:
    normalized = {_norm_key(k): v for k, v in facts.items()}
    for name in names:
        key = _norm_key(name)
        if key in normalized and normalized[key] != "":
            return normalized[key]
    # fuzzy contains
    for name in names:
        key = _norm_key(name)
        for k, v in normalized.items():
            if key and key in k and v != "":
                return v
    return None


def parse_information_firmware(html: str) -> Dict[str, Any]:
    m = re.search(
        r"<H2>\s*Firmware\s*</H2>(.*?)(?:<H2>|</FORM>|</BODY>)",
        html,
        re.I | re.S,
    )
    block = m.group(1) if m else html
    facts = _facts_dict(block)
    info: Dict[str, str] = dict(facts)

    vm = re.search(
        r"Version</b>\s*</TD>\s*<TD[^>]*>\s*([^<]+)\s*</TD>",
        html,
        re.I,
    )
    if vm:
        info.setdefault("Version", vm.group(1).strip())
    dts = re.search(
        r"DTS Version</b>\s*</TD>\s*<TD[^>]*>\s*([^<]+)\s*</TD>",
        html,
        re.I,
    )
    if dts:
        info.setdefault("DTS Version", dts.group(1).strip())

    return {
        "source": INFO_FIRMWARE_URL,
        "firmware": info,
        "write_allowed": False,
        "note": "Firmware Update / Web Update / Add New Feature are blocked by the API.",
    }


def fetch_firmware_info(client: DenonSetupClient) -> Dict[str, Any]:
    html = client.get(INFO_FIRMWARE_URL)
    data = parse_information_firmware(html)
    # Extra sections from Information page (Audio/Video signal etc.)
    data["information_facts"] = _facts_dict(html)
    try:
        fw_form = client.parse_form(client.get(FIRMWARE_PAGE_URL))
        data["notifications"] = {
            "update": _field_value(fw_form.fields, "radioUpdateNotification"),
            "upgrade": _field_value(fw_form.fields, "radioUpgradeNotification"),
        }
        data["firmware_page_title"] = fw_form.title
    except Exception as exc:  # noqa: BLE001
        data["notifications_error"] = str(exc)
    return data


def _merge_network_from_html(html: str) -> Dict[str, Any]:
    form = DenonSetupClient.parse_form(DenonSetupClient("192.168.20.50"), html)
    fields = form.fields
    facts = _facts_dict(html)

    dhcp = _field_value(fields, "radioNetworkSettingDHCP")
    if not dhcp:
        dhcp = _pick_fact(facts, "DHCP")

    ip = _field_value(fields, "textNetworkSettingIPAddress") or _pick_fact(
        facts, "IP Address", "IPAddress"
    )
    mask = _field_value(fields, "textNetworkSettingSubnetMask") or _pick_fact(
        facts, "Subnet Mask", "SubnetMask"
    )
    gw = _field_value(fields, "textNetworkSettingGateway") or _pick_fact(
        facts, "Gateway", "Default Gateway"
    )
    dns1 = _field_value(fields, "textNetworkSettingPrimaryDNS") or _pick_fact(
        facts, "Primary DNS", "DNS"
    )
    dns2 = _field_value(fields, "textNetworkSettingSecondaryDNS") or _pick_fact(
        facts, "Secondary DNS"
    )
    proxy = _field_value(fields, "radioNetworkSettingProxy_OnOff") or _pick_fact(
        facts, "Proxy"
    )
    proxy_port = _field_value(fields, "textNetworkSettingProxyPort") or _pick_fact(
        facts, "Port", "Proxy Port"
    )

    wifi = _field_value(fields, "radioWifi")
    wifi_how = _field_value(fields, "listWifi_WifiSetupHow")

    return {
        "title": form.title,
        "dhcp": dhcp,
        "ip_address": ip or "",
        "subnet_mask": mask or "",
        "gateway": gw or "",
        "primary_dns": dns1 or "",
        "secondary_dns": dns2 or "",
        "proxy": proxy,
        "proxy_port": proxy_port or "",
        "wifi": wifi,
        "wifi_setup_how": wifi_how,
        "fields": fields,
        "text_facts": facts,
    }


def fetch_network_info(client: DenonSetupClient) -> Dict[str, Any]:
    settings_html = client.get(NETWORK_SETTINGS_URL)
    settings = _merge_network_from_html(settings_html)

    connection: Dict[str, Any] = {}
    try:
        connection = _merge_network_from_html(client.get(NETWORK_CONNECTION_URL))
    except Exception as exc:  # noqa: BLE001
        connection = {"error": str(exc)}

    # Prefer non-empty values from settings, then connection
    def prefer(*vals: Optional[str]) -> str:
        for v in vals:
            if v is not None and str(v).strip() != "":
                return str(v)
        return ""

    out: Dict[str, Any] = {
        "source": {
            "settings": NETWORK_SETTINGS_URL,
            "connection": NETWORK_CONNECTION_URL,
            "friendly_name": NETWORK_FRIENDLY_URL,
            "network_control": NETWORK_CONTROL_URL,
        },
        "title": settings.get("title") or "Network",
        "dhcp": prefer(settings.get("dhcp"), connection.get("dhcp")),
        "ip_address": prefer(settings.get("ip_address"), connection.get("ip_address")),
        "subnet_mask": prefer(
            settings.get("subnet_mask"), connection.get("subnet_mask")
        ),
        "gateway": prefer(settings.get("gateway"), connection.get("gateway")),
        "primary_dns": prefer(
            settings.get("primary_dns"), connection.get("primary_dns")
        ),
        "secondary_dns": prefer(
            settings.get("secondary_dns"), connection.get("secondary_dns")
        ),
        "proxy": prefer(settings.get("proxy"), connection.get("proxy")),
        "proxy_port": prefer(settings.get("proxy_port"), connection.get("proxy_port")),
        "wifi": prefer(settings.get("wifi"), connection.get("wifi")),
        "wifi_setup_how": prefer(
            settings.get("wifi_setup_how"), connection.get("wifi_setup_how")
        ),
        "settings": settings,
        "connection": connection,
        "write_allowed": False,
        "note": "Network IP/DHCP/Proxy writes are blocked by the API (read-only).",
    }

    try:
        friendly = client.parse_form(client.get(NETWORK_FRIENDLY_URL))
        out["friendly_name"] = _field_value(friendly.fields, "Friendlyname")
        # template select
        out["friendly_name_template"] = _field_value(
            friendly.fields, "listFriendlyNameTemplete"
        )
    except Exception as exc:  # noqa: BLE001
        out["friendly_name_error"] = str(exc)

    try:
        control = client.parse_form(client.get(NETWORK_CONTROL_URL))
        out["network_standby"] = _field_value(control.fields, "radioNetworkStandby")
        out["network_control_fields"] = control.fields
    except Exception as exc:  # noqa: BLE001
        out["network_standby_error"] = str(exc)

    # Fall back to last scrape text_facts if live fields are empty
    if not out["ip_address"]:
        try:
            eps = json.loads((PROTOCOL_DIR / "endpoints.json").read_text(encoding="utf-8"))
            for e in eps:
                if "NETWORK/SETTINGS/s_network_setting_dhcp.asp" in e.get(
                    "submit_url", ""
                ):
                    facts = e.get("text_facts") or {}
                    out["ip_address"] = prefer(
                        out["ip_address"],
                        facts.get("IP Address"),
                        facts.get("-IP Address"),
                    )
                    out["subnet_mask"] = prefer(
                        out["subnet_mask"], facts.get("Subnet Mask")
                    )
                    out["gateway"] = prefer(out["gateway"], facts.get("Gateway"))
                    out["dhcp"] = prefer(out["dhcp"], facts.get("DHCP"))
                    out["scrape_text_facts"] = facts
        except Exception as exc:  # noqa: BLE001
            out["scrape_fallback_error"] = str(exc)

    return out


def _facts_to_items(facts: Dict[str, str]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for k, v in (facts or {}).items():
        label = clean_display_text(k)
        if not label:
            continue
        items.append({"label": label, "value": clean_display_text(v)})
    return items


def fetch_information_overview(client: DenonSetupClient) -> Dict[str, Any]:
    """Human-friendly Overview sections from General → Information."""
    from .information_page import sections_as_dashboard_cards

    html = client.get(INFO_FIRMWARE_URL)
    return {
        "source": INFO_FIRMWARE_URL,
        "write_allowed": False,
        "sections": sections_as_dashboard_cards(html),
    }


def fetch_info_dashboard(client: DenonSetupClient) -> Dict[str, Any]:
    """Combined human-readable info for the UI Info tab."""
    fw = fetch_firmware_info(client)
    net = fetch_network_info(client)
    overview = fetch_information_overview(client)

    network_items = [
        {"label": "Friendly Name", "value": net.get("friendly_name") or ""},
        {"label": "DHCP", "value": net.get("dhcp") or ""},
        {"label": "IP Address", "value": net.get("ip_address") or ""},
        {"label": "Subnet Mask", "value": net.get("subnet_mask") or ""},
        {"label": "Gateway", "value": net.get("gateway") or ""},
        {"label": "Primary DNS", "value": net.get("primary_dns") or ""},
        {"label": "Secondary DNS", "value": net.get("secondary_dns") or ""},
        {"label": "Proxy", "value": net.get("proxy") or ""},
        {"label": "Network Control", "value": net.get("network_standby") or ""},
    ]
    network_items = [i for i in network_items if i["value"] not in (None, "")]

    firmware_items = [
        {"label": k, "value": str(v)}
        for k, v in (fw.get("firmware") or {}).items()
        if v not in (None, "")
        and not re.search(r"update\s*notification|upgrade\s*notification", str(k), re.I)
    ]
    # Update/Upgrade Notification toggles belong on General → Firmware settings,
    # not in Information → Firmware (version / DTS only).
    cards = [
        {"id": "network", "title": "Network", "items": network_items},
        {"id": "firmware", "title": "Firmware", "items": firmware_items},
    ]
    # Prefer live Information-page structure for Audio/Video/ZONE/… cards.
    # Drop duplicate firmware/alerts from overview when we already have firmer sources.
    seen = {"network", "firmware"}
    for sec in overview.get("sections") or []:
        sid = sec.get("id") or ""
        if sid in seen:
            continue
        if sid == "firmware_signal" and firmware_items:
            continue
        if sid == "alerts" and not sec.get("items"):
            # Alerts control lives on the Information editor; keep a placeholder card
            cards.append(
                {
                    "id": "alerts",
                    "title": "Notifications",
                    "items": [
                        {
                            "label": "Notification Alerts",
                            "value": "See General → Information",
                        }
                    ],
                }
            )
            seen.add("alerts")
            continue
        if not sec.get("items") and sid != "alerts":
            continue
        cards.append(sec)
        seen.add(sid)

    # Ensure firmware card sits above Notifications when both present
    ordered_ids = [
        "network",
        "audio",
        "video",
        "hdmi_monitor",
        "zones",
        "firmware",
        "alerts",
    ]
    by_id = {c["id"]: c for c in cards if c.get("id")}
    ordered = [by_id[i] for i in ordered_ids if i in by_id]
    for c in cards:
        if c.get("id") not in {x["id"] for x in ordered}:
            ordered.append(c)

    return {
        "write_allowed": False,
        "cards": ordered,
        "note": "Read-only. Firmware update and network IP/DHCP writes are blocked.",
    }
