"""Denon X1200W SETUP HTTP client — generic read / submit using scraped protocol."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from .safety import SAFE_FORCED_FIELDS, NETWORK_WRITE_FIELDS, WRITE_UNLOCKED_ENDPOINT_IDS, sanitize_write_fields
from .field_labels import clean_display_text

ATTR = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(['"])(.*?)\2""", re.S)


def _attrs(tag_html: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in ATTR.finditer(tag_html):
        out[m.group(1).lower()] = m.group(3)
    low = tag_html.lower()
    for b in ("checked", "selected", "disabled", "readonly"):
        # Boolean HTML attrs may appear bare, ="", or =checked (no quotes).
        if re.search(rf"""\b{b}(?:\s*=\s*(?:['"][^'"]*['"]|{b}|true|false))?\b""", low):
            out[b] = "true"
    return out


def _set_radio_value(fields: Dict[str, Any], name: str, value: str) -> None:
    meta = fields.get(name)
    if not isinstance(meta, dict) or meta.get("type") != "radio":
        return
    meta["value"] = value
    opts = meta.get("options")
    if isinstance(opts, list):
        for opt in opts:
            if isinstance(opt, dict):
                opt["selected"] = str(opt.get("value")) == str(value)


def _infer_missing_radio_values(fields: Dict[str, Any]) -> None:
    """Fill radio values Denon sometimes omits (no checked= on the input).

    Network Settings is the known case: DHCP/Proxy radios often lack ``checked``,
    while dependent text fields are ``disabled`` (or Port stays 00000) to reflect
    the live state — same greying Denon's web UI shows.
    """
    dhcp = fields.get("radioNetworkSettingDHCP")
    if isinstance(dhcp, dict) and dhcp.get("value") in (None, ""):
        ip_fields = [
            fields.get(n)
            for n in (
                "textNetworkSettingIPAddress",
                "textNetworkSettingSubnetMask",
                "textNetworkSettingGateway",
                "textNetworkSettingPrimaryDNS",
                "textNetworkSettingSecondaryDNS",
            )
        ]
        metas = [m for m in ip_fields if isinstance(m, dict)]
        if metas and all(bool(m.get("disabled")) for m in metas):
            _set_radio_value(fields, "radioNetworkSettingDHCP", "ON")
        elif metas and any(not m.get("disabled") for m in metas):
            _set_radio_value(fields, "radioNetworkSettingDHCP", "OFF")

    proxy = fields.get("radioNetworkSettingProxy_OnOff")
    if isinstance(proxy, dict) and proxy.get("value") in (None, ""):
        # Ensure Off / On(Address) / On(Name) options always exist.
        opts = proxy.get("options")
        if not isinstance(opts, list) or len(opts) < 2:
            proxy["options"] = [
                {"value": "OFF", "label": "Off", "selected": False},
                {"value": "ADR", "label": "On(Address)", "selected": False},
                {"value": "NAM", "label": "On(Name)", "selected": False},
            ]
        port = fields.get("textNetworkSettingProxyPort")
        if isinstance(port, dict):
            pval = str(port.get("value") or "").strip()
            # Denon greys Port when Proxy is Off (disabled and/or 00000).
            if port.get("disabled") or pval in ("", "0", "00000"):
                _set_radio_value(fields, "radioNetworkSettingProxy_OnOff", "OFF")
            elif pval.isdigit() and int(pval) > 0 and not port.get("disabled"):
                # Proxy is on; Address vs Name is unknown without checked — Address.
                _set_radio_value(fields, "radioNetworkSettingProxy_OnOff", "ADR")
        else:
            # No port field in form — Denon default is Off.
            _set_radio_value(fields, "radioNetworkSettingProxy_OnOff", "OFF")


@dataclass
class ParsedForm:
    name: str
    action: str
    method: str
    fields: Dict[str, Any] = field(default_factory=dict)
    title: str = ""


class DenonSetupClient:
    def __init__(
        self,
        host: str = "192.168.20.50",
        *,
        timeout: float = 20.0,
        settle_seconds: float = 0.6,
    ) -> None:
        host = host.rstrip("/")
        self.base = host if host.startswith("http") else f"http://{host}"
        self.timeout = timeout
        self.settle_seconds = settle_seconds

    def request(
        self,
        method: str,
        url: str,
        data: Optional[Mapping[str, str]] = None,
    ) -> str:
        if url.startswith("/"):
            url = urljoin(self.base + "/", url.lstrip("/"))
        elif not url.startswith("http"):
            url = urljoin(self.base + "/", url)

        body: Optional[bytes] = None
        headers = {
            "User-Agent": "denon-x1200w-api/1.0",
            "Accept": "text/html,*/*",
        }
        if data is not None:
            body = urlencode(list(data.items())).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = Request(url, data=body, headers=headers, method=method.upper())
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            text = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
            raise RuntimeError(f"HTTP {e.code} for {url}: {text[:300]}") from e
        except URLError as e:
            raise RuntimeError(f"Connection error for {url}: {e}") from e

        if self.settle_seconds and method.upper() == "POST":
            time.sleep(self.settle_seconds)
        return text

    def get(self, url: str) -> str:
        return self.request("GET", url)

    def post(self, url: str, data: Mapping[str, str]) -> str:
        return self.request("POST", url, data)

    def post_multipart(
        self,
        url: str,
        *,
        fields: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Tuple[str, bytes, str]]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """POST multipart/form-data (local firmware upload).

        ``files`` values are ``(filename, content_bytes, content_type)``.
        """
        if url.startswith("/"):
            url = urljoin(self.base + "/", url.lstrip("/"))
        elif not url.startswith("http"):
            url = urljoin(self.base + "/", url)

        boundary = f"----DenonFirmwareBoundary{int(time.time() * 1000)}"
        body = bytearray()

        def add_field(name: str, value: str) -> None:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(
                    "utf-8"
                )
            )
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")

        def add_file(
            name: str, filename: str, content: bytes, content_type: str
        ) -> None:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8")
            )
            body.extend(
                f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n".encode(
                    "utf-8"
                )
            )
            body.extend(content)
            body.extend(b"\r\n")

        for k, v in (fields or {}).items():
            add_field(k, v)
        for k, meta in (files or {}).items():
            fname, content, ctype = meta
            add_file(k, fname, content, ctype)
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        headers = {
            "User-Agent": "denon-x1200w-api/1.0",
            "Accept": "text/html,*/*",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        }
        req = Request(url, data=bytes(body), headers=headers, method="POST")
        use_timeout = self.timeout if timeout is None else timeout
        try:
            with urlopen(req, timeout=use_timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            text = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
            raise RuntimeError(f"HTTP {e.code} for {url}: {text[:300]}") from e
        except URLError as e:
            raise RuntimeError(f"Connection error for {url}: {e}") from e
        if self.settle_seconds:
            time.sleep(self.settle_seconds)
        return text

    def parse_form(self, html: str) -> ParsedForm:
        title = ""
        m = re.search(r'<div class="Title">\s*(.*?)\s*</div>', html, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()

        fm = re.search(r"<form\b([^>]*)>(.*?)</form>", html, re.I | re.S)
        if not fm:
            return ParsedForm(name="", action="", method="GET", title=title)

        fa = _attrs(fm.group(1))
        body = fm.group(2)
        fields: Dict[str, Any] = {}

        # Map first control name in a table row → nearby <B> label text
        row_labels: Dict[str, str] = {}
        column_headers = {"HDMI", "DIGITAL", "ANALOG", "VIDEO", "COMPONENT", "COMP"}
        for rm in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", body, re.I | re.S):
            row = rm.group(1)
            bm = re.search(r"<b[^>]*>\s*(.*?)\s*</b>", row, re.I | re.S)
            if not bm:
                continue
            label = clean_display_text(
                re.sub(r"&nbsp;", " ", bm.group(1), flags=re.I)
            )
            if not label or label.upper() in column_headers:
                continue
            for im in re.finditer(r"<input\b([^>]*)/?>|<select\b([^>]*)>", row, re.I):
                a = _attrs(im.group(1) or im.group(2) or "")
                name = a.get("name")
                if not name or name.startswith("defBtn") or name.startswith("defbtn"):
                    continue
                if name and name not in row_labels:
                    row_labels[name] = label

        # radios grouped by name — capture display text after each input
        radios: Dict[str, List[Dict[str, Any]]] = {}
        for im in re.finditer(r"<input\b([^>]*)/?>", body, re.I):
            a = _attrs(im.group(1))
            name = a.get("name")
            if not name:
                continue
            itype = a.get("type", "text").lower()
            if itype == "radio":
                end = im.end()
                nxt = re.search(r"<input\b|<select\b|<tr\b|</td\b|</tr\b", body[end:], re.I)
                chunk = body[end : end + (nxt.start() if nxt else 40)]
                display = clean_display_text(chunk)
                radios.setdefault(name, []).append(
                    {
                        "value": a.get("value", ""),
                        "label": display or a.get("value", ""),
                        "checked": "checked" in a,
                        "disabled": "disabled" in a,
                    }
                )
                continue
            if itype == "button":
                continue
            fields[name] = {
                "type": itype,
                "value": a.get("value", ""),
                "disabled": "disabled" in a,
                "min": a.get("min"),
                "max": a.get("max"),
                "step": a.get("step"),
            }
            if name in row_labels:
                fields[name]["ui_label"] = row_labels[name]

        # Channel Levels + Manual EQ: unnamed Range* sliders + hidden text* fields.
        # Hidden fields alone are stripped from API responses, so promote them to range.
        ranges_by_key: Dict[str, Dict[str, str]] = {}
        for im in re.finditer(r"<input\b([^>]*)/?>", body, re.I):
            a = _attrs(im.group(1))
            if a.get("type", "").lower() != "range":
                continue
            rid = a.get("id") or ""
            m = re.match(r"^Range((?:CV|GEQ).+)$", rid, re.I)
            if not m:
                continue
            key = m.group(1).upper()
            is_geq = key.startswith("GEQ")
            ranges_by_key[key] = {
                "value": a.get("value", ""),
                "min": a.get("min", "-20" if is_geq else "-12"),
                "max": a.get("max", "6" if is_geq else "12"),
                "step": a.get("step", "0.5"),
            }
        for name, meta in list(fields.items()):
            if name.startswith("textCV"):
                key = name[4:].upper()  # textCVFL → CVFL
                default_min, default_max = "-12", "12"
            elif name.startswith("textGEQ"):
                key = name[4:].upper()  # textGEQ63 → GEQ63
                default_min, default_max = "-20", "6"
            else:
                continue
            rng = ranges_by_key.get(key)
            if not rng:
                # Still expose editable number even without a paired range node
                if meta.get("type") == "hidden":
                    meta["type"] = "number"
                    meta["min"] = meta.get("min") or default_min
                    meta["max"] = meta.get("max") or default_max
                    meta["step"] = meta.get("step") or "0.5"
                    meta["unit"] = "dB"
                continue
            meta["type"] = "range"
            meta["min"] = rng.get("min") or default_min
            meta["max"] = rng.get("max") or default_max
            meta["step"] = rng.get("step") or "0.5"
            # Prefer the named hidden field value (what Denon POSTs). Only fill from
            # the unpaired Range* widget when the hidden value is missing.
            if meta.get("value") in (None, "") and rng.get("value") not in (None, ""):
                meta["value"] = rng["value"]
            meta["unit"] = "dB"
            fields[name] = meta

        for name, options in radios.items():
            selected = next((o["value"] for o in options if o["checked"]), None)
            fields[name] = {
                "type": "radio",
                "value": selected,
                "options": [
                    {
                        "value": o["value"],
                        "label": o.get("label") or o["value"],
                        "selected": o.get("checked", False),
                    }
                    for o in options
                ],
            }
            if name in row_labels:
                fields[name]["ui_label"] = row_labels[name]

        for sm in re.finditer(
            r"<select\b([^>]*)>(.*?)</select>", body, re.I | re.S
        ):
            a = _attrs(sm.group(1))
            name = a.get("name")
            if not name:
                continue
            opts = []
            selected = None
            for om in re.finditer(
                r"<option\b([^>]*)>(.*?)</option>", sm.group(2), re.I | re.S
            ):
                oa = _attrs(om.group(1))
                label = clean_display_text(om.group(2))
                val = oa.get("value", "")
                if not label and val.upper() == "OFF":
                    label = "-"
                is_sel = "selected" in oa
                if is_sel:
                    selected = val
                opts.append({"value": val, "label": label or val, "selected": is_sel})
            fields[name] = {
                "type": "select",
                "value": selected,
                "options": opts,
                "disabled": "disabled" in a,
            }
            if name in row_labels:
                fields[name]["ui_label"] = row_labels[name]

        # Crossovers: inactive mode rows are plain text (no <select>), e.g. "All 80Hz"
        # when Speaker Selection is Individual. Capture so the UI can still show them.
        crossover_labels = {
            "all": "listCrossFreqAll",
            "front": "listCrossFreqAdvFr",
            "center": "listCrossFreqAdvC",
            "surround": "listCrossFreqAdvSr",
            "top middle": "listCrossFreqAdvTopMiddle",
        }
        # HDMI Setup status rows (no controls)
        hdmi_static = {
            "hdmi audio out": ("_display_hdmi_audio_out", "HDMI Audio Out"),
            "arc": ("_display_hdmi_arc", " -ARC"),
            "-arc": ("_display_hdmi_arc", " -ARC"),
            "hdmi pass through": ("_display_hdmi_pass", " -HDMI Pass Through"),
            "-hdmi pass through": ("_display_hdmi_pass", " -HDMI Pass Through"),
        }
        for rm in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", body, re.I | re.S):
            row = rm.group(1)
            bm = re.search(r"<b[^>]*>\s*(.*?)\s*</b>", row, re.I | re.S)
            if not bm:
                continue
            label = clean_display_text(
                re.sub(r"&nbsp;", " ", bm.group(1), flags=re.I)
            )
            if not label:
                continue
            key = label.lower().strip()
            fname = crossover_labels.get(key)
            if fname and fname not in fields and not re.search(
                r"<select\b|<input\b", row, re.I
            ):
                plain = clean_display_text(re.sub(r"<[^>]+>", " ", row))
                hz = ""
                m_hz = re.search(r"(\d+\s*Hz)", plain, re.I)
                if m_hz:
                    hz = re.sub(r"\s+", "", m_hz.group(1))
                fields[fname] = {
                    "type": "display",
                    "value": hz,
                    "options": [],
                    "ui_label": label,
                    "inactive": True,
                }
                continue

            # Normalize leading dash/spaces for HDMI static rows
            key_norm = re.sub(r"^[\s\-–—]+", "", key).strip()
            mapped = hdmi_static.get(key) or hdmi_static.get(key_norm)
            if not mapped:
                continue
            fname, nice = mapped
            if fname in fields:
                continue
            if re.search(r"<select\b|<input\b", row, re.I):
                continue
            plain = clean_display_text(re.sub(r"<[^>]+>", " ", row))
            # Drop label text from value
            val = plain
            for chunk in (label, nice, nice.lstrip(" -")):
                if chunk and val.lower().startswith(chunk.lower()):
                    val = val[len(chunk) :].strip()
            fields[fname] = {
                "type": "display",
                "value": val or plain,
                "options": [],
                "ui_label": nice,
                "label": nice,
                "indent": nice.strip().startswith("-"),
            }

        # Subwoofer Level Adjust: when Off, level is plain text e.g. "+ 5.0 dB"
        for rm in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", body, re.I | re.S):
            row = rm.group(1)
            bm = re.search(r"<b[^>]*>\s*(.*?)\s*</b>", row, re.I | re.S)
            if not bm:
                continue
            label = clean_display_text(
                re.sub(r"&nbsp;", " ", bm.group(1), flags=re.I)
            )
            if label.lower().strip() != "subwoofer level":
                continue
            if re.search(r"<select\b|<input\b", row, re.I):
                continue
            plain = clean_display_text(re.sub(r"<[^>]+>", " ", row))
            val = plain
            if val.lower().startswith("subwoofer level"):
                val = val[len("subwoofer level") :].strip()
            fields["_display_sw_level"] = {
                "type": "display",
                "value": val or plain,
                "options": [],
                "ui_label": "Subwoofer Level",
                "label": "Subwoofer Level",
            }

        _infer_missing_radio_values(fields)
        return ParsedForm(
            name=fa.get("name", ""),
            action=fa.get("action", ""),
            method=fa.get("method", "GET").upper(),
            fields=fields,
            title=clean_display_text(title),
        )

    def _warm_setup_frames(self, read_url: str) -> None:
        """Hit parent frames before pages that often omit radio ``checked``.

        Firmware Notifications and Network DHCP/Proxy sometimes only include the
        live selection after the left/frame shell has been requested.
        """
        path = urlparse(read_url if "://" in read_url else urljoin(self.base + "/", read_url.lstrip("/"))).path
        warmers: List[str] = []
        if "/FIRMWARE/" in path.upper():
            warmers = [
                "/SETUP/GENERAL/FIRMWARE/f_firmware.asp",
                "/SETUP/GENERAL/FIRMWARE/d_left_firmware.asp",
            ]
        elif "/NETWORK/SETTINGS/" in path.upper():
            warmers = [
                "/SETUP/NETWORK/SETTINGS/f_network_setting_dhcp.asp",
                "/SETUP/NETWORK/SETTINGS/d_left_network_setting_dhcp.asp",
            ]
        for w in warmers:
            try:
                self.get(w)
            except RuntimeError:
                pass

    def read_page(self, read_url: str) -> Dict[str, Any]:
        path_u = (read_url or "").upper()
        if any(
            x in path_u
            for x in (
                "/FIRMWARE/",
                "/NETWORK/SETTINGS/",
            )
        ):
            self._warm_setup_frames(read_url)
        html = self.get(read_url)
        parsed = self.parse_form(html)
        action_abs = (
            urljoin(read_url, parsed.action) if parsed.action else read_url
        )
        return {
            "read_url": read_url,
            "title": parsed.title,
            "form_name": parsed.name,
            "submit_url": action_abs,
            "method": parsed.method,
            "fields": parsed.fields,
            "reachable": True,
        }

    @staticmethod
    def _geq_band_fingerprint(fields: Mapping[str, Any]) -> Tuple[str, ...]:
        """Stable identity for Manual EQ band rows (channel + textGEQ*)."""
        ch = ""
        sp = ""
        meta_ch = fields.get("listGEQAdjustEQ") if isinstance(fields, dict) else None
        meta_sp = fields.get("listGEQSpSelection") if isinstance(fields, dict) else None
        if isinstance(meta_ch, dict):
            ch = str(meta_ch.get("value") or "")
        if isinstance(meta_sp, dict):
            sp = str(meta_sp.get("value") or "")
        bands: List[str] = []
        for name in (
            "textGEQ63",
            "textGEQ125",
            "textGEQ250",
            "textGEQ500",
            "textGEQ1k",
            "textGEQ2k",
            "textGEQ4k",
            "textGEQ8k",
            "textGEQ16k",
        ):
            meta = fields.get(name) if isinstance(fields, dict) else None
            if isinstance(meta, dict):
                bands.append(str(meta.get("value") or ""))
            else:
                bands.append("")
        return (ch, sp, *bands)

    def read_page_stable(
        self, read_url: str, *, retries: int = 2, pause: float = 0.35
    ) -> Dict[str, Any]:
        """Re-read Manual EQ until two consecutive snapshots match.

        Denon's SETUP page can briefly return another channel's curve (or a
        mid-write form) under concurrent access; that looked like +/- flipping.
        """
        first = self.read_page(read_url)
        fp = self._geq_band_fingerprint(first.get("fields") or {})
        for _ in range(max(0, retries)):
            if pause:
                time.sleep(pause)
            nxt = self.read_page(read_url)
            fp2 = self._geq_band_fingerprint(nxt.get("fields") or {})
            if fp2 == fp and any(fp2[2:]):  # bands present and stable
                return nxt
            first, fp = nxt, fp2
        return first

    def submit(
        self,
        submit_url: str,
        fields: Mapping[str, str],
        *,
        read_url: Optional[str] = None,
        merge_defaults: bool = True,
        endpoint_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: MutableMapping[str, str] = {}
        if merge_defaults and read_url:
            current = self.read_page(read_url)
            for name, meta in current["fields"].items():
                val = meta.get("value")
                if val is None:
                    continue
                if name.startswith("setbtn") or name.startswith("setBtn"):
                    continue
                if name.startswith("defBtn") or name.startswith("defbtn"):
                    continue
                if str(meta.get("type")) in ("button", "submit"):
                    continue
                payload[name] = str(val)
            for flag in (
                "setAdjustEQ",
                "setGEQCurveCopy",
                "setGEQSetDefaults",
                "setAudioDelay",
                "setMainPwOnLevel",
                "setSourceLevelDigital",
                "setCLA",
                "setDelayTimeAllSet",
                "setUpdateCheck",
                "setAddNewFeature",
                "setFirmwareUpdateWebUpdate",
                "setFuncRenameDefault",
                "setFuncRenameAll",
                "setFuncRenameBD",
                "setFuncRenameMPLAY",
                "buttonNet",
                "FriendlySet",
                "FriendlyDef",
                "setZoneRenameAll",
                "setZoneRenameDefault",
                "setQuickSelectName",
                "setQuickSelectNameAll",
                "setLfeLevel",
            ):
                if flag in current["fields"] and flag not in fields:
                    payload[flag] = "off"

        payload.update({k: str(v) for k, v in fields.items()})
        # Never echo Denon submit/button names unless the caller set them explicitly.
        for submit_only in (
            "setBtnQuickSelectNameDefault",
            "setbtnQuickSelectNameAll",
            "setbtnLfeLevel",
        ):
            if submit_only not in fields:
                payload.pop(submit_only, None)
        # Manual EQ: Denon listBox()/radioBtn() submit the whole form, but band values
        # must only apply when Set / Curve Copy / Set Defaults is pressed. Echoing
        # textGEQ* from a raced read-back (merge_defaults) flips curves between
        # speakers / transient pages.
        if (endpoint_id or "").lower() == "audio_graphiceq_s_audio":
            applying_bands = (
                str(payload.get("setAdjustEQ", "off")).lower() == "set"
                or str(payload.get("setGEQCurveCopy", "off")).lower() == "set"
                or str(payload.get("setGEQSetDefaults", "off")).lower() == "set"
            )
            if not applying_bands:
                for key in list(payload):
                    if key.startswith("textGEQ"):
                        payload.pop(key, None)
        payload = sanitize_write_fields(dict(payload), endpoint_id=endpoint_id)
        # Keep forced safe flags on unrelated forms; unlocked Setup Lock keeps radioSetupLock.
        payload.update(SAFE_FORCED_FIELDS)
        unlocked = (endpoint_id or "").lower() in {
            x.lower() for x in WRITE_UNLOCKED_ENDPOINT_IDS
        }
        if unlocked and "radioSetupLock" in fields:
            payload["radioSetupLock"] = str(fields["radioSetupLock"])
        if unlocked and (endpoint_id or "").lower() == "general_firmware_s_firmware":
            for name in ("radioUpdateNotification", "radioUpgradeNotification"):
                if name in fields:
                    payload[name] = str(fields[name])
            for name in (
                "setUpdateCheck",
                "setAddNewFeature",
                "setFirmwareUpdateWebUpdate",
                "setFirmwareUpdate",
            ):
                payload[name] = "off"
        if unlocked and (endpoint_id or "").lower() == "general_information_s_information":
            if "radioAlerts" in fields:
                payload["radioAlerts"] = str(fields["radioAlerts"])
        if unlocked and (endpoint_id or "").lower() in {
            "network_settings_s_network_setting_dhcp",
            "network_connection_s_network_setting_dhcp",
        }:
            for name in NETWORK_WRITE_FIELDS:
                if name in fields:
                    payload[name] = str(fields[name])
        self.post(submit_url, payload)
        result: Dict[str, Any] = {"submitted": dict(payload), "submit_url": submit_url}
        if read_url:
            if (endpoint_id or "").lower() == "audio_graphiceq_s_audio":
                result["after"] = self.read_page_stable(read_url)
            else:
                result["after"] = self.read_page(read_url)
        return result


def endpoint_id(submit_url: str) -> str:
    path = urlparse(submit_url).path
    if "/SETUP/" in path:
        path = path.split("/SETUP/", 1)[1]
    return path.replace("/", "_").replace(".asp", "").lower()
