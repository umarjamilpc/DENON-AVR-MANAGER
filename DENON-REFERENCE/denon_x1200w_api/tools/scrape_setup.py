#!/usr/bin/env python3
"""GET-only deep scrape of Denon SETUP UI with safety exclusions."""

from __future__ import annotations

import json
import re
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

HOST = "http://192.168.20.50"
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "tools" / "scrape_out"
RAW_DIR = OUT_DIR / "raw"
PROTOCOL_DIR = ROOT / "protocol"

START = [
    f"{HOST}/SETUP/f_home.asp",
    f"{HOST}/SETUP/AUDIO/f_audio.asp",
    f"{HOST}/SETUP/VIDEO/f_video.asp",
    f"{HOST}/SETUP/INPUTS/f_inputs.asp",
    f"{HOST}/SETUP/SPEAKERS/f_speakers.asp",
    f"{HOST}/SETUP/NETWORK/f_network.asp",
    f"{HOST}/SETUP/GENERAL/f_general.asp",
    # Section menus
    f"{HOST}/SETUP/AUDIO/MENU/d_right_audio.asp",
    f"{HOST}/SETUP/VIDEO/MENU/d_right_video.asp",
    f"{HOST}/SETUP/INPUTS/MENU/d_right_inputsetup.asp",
    f"{HOST}/SETUP/SPEAKERS/MENU/d_right_speakers.asp",
    f"{HOST}/SETUP/NETWORK/MENU/d_right_network.asp",
    f"{HOST}/SETUP/GENERAL/MENU/d_right_general.asp",
    # Network / info (read)
    f"{HOST}/SETUP/NETWORK/CONNECTION/f_network_setting_dhcp.asp",
    f"{HOST}/SETUP/NETWORK/SETTINGS/f_network_setting_dhcp.asp",
    f"{HOST}/SETUP/NETWORK/IPCONTROL/f_network.asp",
    f"{HOST}/SETUP/NETWORK/FRIENDLYNAME/f_network.asp",
    f"{HOST}/SETUP/GENERAL/INFORMATION/f_information.asp",
    f"{HOST}/SETUP/GENERAL/FIRMWARE/f_firmware.asp",
    # Greyed-out / mode-dependent pages (direct URLs still work) — GET-only seeds
    f"{HOST}/SETUP/AUDIO/DIALOGLEVEL/f_audio.asp",
    f"{HOST}/SETUP/AUDIO/DIALOGLEVEL/d_audio.asp",
    f"{HOST}/SETUP/AUDIO/SUBWOOFERLEVEL/f_audio.asp",
    f"{HOST}/SETUP/AUDIO/SUBWOOFERLEVEL/d_audio.asp",
    f"{HOST}/SETUP/AUDIO/RESTORER/f_audio.asp",
    f"{HOST}/SETUP/AUDIO/RESTORER/d_audio.asp",
    f"{HOST}/SETUP/AUDIO/GRAPHICEQ/f_audio.asp",
    f"{HOST}/SETUP/AUDIO/GRAPHICEQ/d_audio.asp",
    f"{HOST}/SETUP/AUDIO/SURROUNDPARAMETER/f_audio.asp",
    f"{HOST}/SETUP/AUDIO/SURROUNDPARAMETER/d_audio.asp",
    f"{HOST}/SETUP/AUDIO/AUDIODELAY/f_audio.asp",
    f"{HOST}/SETUP/AUDIO/AUDIODELAY/d_audio.asp",
    f"{HOST}/SETUP/AUDIO/VOLUME/f_audio.asp",
    f"{HOST}/SETUP/AUDIO/VOLUME/d_audio.asp",
    f"{HOST}/SETUP/GENERAL/ZONE2SETUP/f_general.asp",
    f"{HOST}/SETUP/GENERAL/ZONE2SETUP/d_general.asp",
    f"{HOST}/SETUP/SPEAKERS/FRONTSPEAKER/f_speakersetup.asp",
    f"{HOST}/SETUP/SPEAKERS/FRONTSPEAKER/d_speakersetup.asp",
    # Inputs explicit
    f"{HOST}/SETUP/INPUTS/INPUTASSIGN/f_InputAssign.asp",
    f"{HOST}/SETUP/INPUTS/SOURCERENAME/f_Rename.asp",
    f"{HOST}/SETUP/INPUTS/HIDESOURCES/f_Delete.asp",
    f"{HOST}/SETUP/INPUTS/SOURCELEVEL/f_inputsetup.asp",
    f"{HOST}/SETUP/INPUTS/INPUTSELECT/f_inputsetup.asp",
    # Speakers explicit
    f"{HOST}/SETUP/SPEAKERS/AMPASSIGN/f_speakersetup.asp",
    f"{HOST}/SETUP/SPEAKERS/SPEAKERCONFIG/f_speakersetup.asp",
    f"{HOST}/SETUP/SPEAKERS/DISTANCES/f_speakersetup.asp",
    f"{HOST}/SETUP/SPEAKERS/LEVELS/f_speakersetup.asp",
    f"{HOST}/SETUP/SPEAKERS/CROSSOVERS/f_speakersetup.asp",
    f"{HOST}/SETUP/SPEAKERS/BASS/f_speakersetup.asp",
    # Video explicit
    f"{HOST}/SETUP/VIDEO/HDMISETUP/f_video.asp",
    f"{HOST}/SETUP/VIDEO/ONSCREENDISPLAY/f_video.asp",
    f"{HOST}/SETUP/VIDEO/TVFORMAT/f_video.asp",
    # General explicit (Setup Lock is READ-scraped only; writes blocked in API)
    f"{HOST}/SETUP/GENERAL/LANGUAGE/f_general.asp",
    f"{HOST}/SETUP/GENERAL/ECO/f_general.asp",
    f"{HOST}/SETUP/GENERAL/ZONERENAME/f_general.asp",
    f"{HOST}/SETUP/GENERAL/SELECTNAMES/f_general.asp",
    f"{HOST}/SETUP/GENERAL/FRONTDISPLAY/f_general.asp",
    f"{HOST}/SETUP/GENERAL/USAGEDATA/f_general.asp",
    f"{HOST}/SETUP/GENERAL/SETUPLOCK/f_general.asp",
    f"{HOST}/SETUP/GENERAL/SETUPLOCK/d_general.asp",
    # Network Diagnostics (manual item; often absent from web menu but URL works)
    f"{HOST}/SETUP/NETWORK/DIAGNOSTICS/f_network.asp",
    f"{HOST}/SETUP/NETWORK/DIAGNOSTICS/d_network.asp",
    # Audio Audyssey *settings* only (MultEQ / DynEQ / DynVol) — NOT Speakers Audyssey Setup wizard
    f"{HOST}/SETUP/AUDIO/AUDYSSEY/f_audio.asp",
    f"{HOST}/SETUP/AUDIO/AUDYSSEY/d_audio.asp",
]

# Never crawl these (critical / write-dangerous / wizards)
SKIP_SUBSTRINGS = (
    "/SAVE/",
    "/LOAD/",
    "f_config_save",
    "f_config_load",
    # Firmware update actions (read of d_firmware / information is allowed via other seeds)
    "s_firmwareupdate",
    "s_addnewfeature",
    "s_updatecheck",
    "d_firmwareupdate",
    "d_addnewfeature",
    "d_updatecheck",
    "formPostHandler",
    "bl_firmware",
    "appFirmware",
    # Service / wizard paths — do not crawl or interact
    "MAINTENANCE",
    "SETUPASSISTANT",
    "BEGINSETUP",
    "SPCALIBRATION",
    "SP.CALIBRATION",
    # Audyssey Setup wizard steps (mic calibration) — never start
    "AUDYSSEYSETUP",
    "AUDYSSEY_SETUP",
    "BEGINTEST",
    "BEGIN_TEST",
    "DOLBYSP",
)

TIMEOUT = 20
SETTLE = 0.2

ATTR_RE = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(['"])(.*?)\2""", re.S)


@dataclass
class FieldInfo:
    tag: str
    name: str
    input_type: str = ""
    value: str = ""
    checked: bool = False
    selected: bool = False
    disabled: bool = False
    options: List[Dict[str, str]] = field(default_factory=list)
    min: str = ""
    max: str = ""
    step: str = ""
    visible_text: str = ""


@dataclass
class FormInfo:
    name: str
    action: str
    method: str
    target: str
    action_abs: str
    fields: List[FieldInfo]


@dataclass
class PageInfo:
    url: str
    title: str
    frames: List[str]
    links: List[str]
    forms: List[FormInfo]
    text_facts: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


def should_skip(url: str) -> bool:
    u = url.lower()
    return any(s.lower() in u for s in SKIP_SUBSTRINGS)


def normalize(url: str, base: str) -> Optional[str]:
    abs_url = urljoin(base, url.strip())
    p = urlparse(abs_url)
    if p.scheme not in ("http", "https"):
        return None
    if p.hostname not in ("192.168.20.50", "localhost"):
        return None
    abs_url = urlunparse((p.scheme, p.netloc, p.path, "", p.query, ""))
    if "/SETUP" not in p.path.upper():
        return None
    if should_skip(abs_url):
        return None
    return abs_url


def fetch(url: str) -> Tuple[int, str]:
    req = Request(
        url,
        headers={"User-Agent": "denon-rescrape/1.1", "Accept": "text/html,*/*"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except URLError as e:
        return 0, f"URLError: {e}"


def attrs(tag_html: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in ATTR_RE.finditer(tag_html):
        out[m.group(1).lower()] = m.group(3)
    low = tag_html.lower()
    for b in ("checked", "selected", "disabled", "readonly"):
        if re.search(rf"\b{b}\b", low):
            out[b] = out.get(b, "true")
    return out


def parse_select(block: str) -> List[Dict[str, str]]:
    options = []
    for m in re.finditer(r"<option\b([^>]*)>(.*?)</option>", block, re.I | re.S):
        a = attrs(m.group(1))
        options.append(
            {
                "value": a.get("value", ""),
                "label": re.sub(r"\s+", " ", m.group(2)).strip(),
                "selected": "selected" in a,
            }
        )
    return options


def extract_text_facts(html: str) -> Dict[str, str]:
    """Label/value pairs from table cells (for IP/version shown as plain text)."""
    facts: Dict[str, str] = {}
    for m in re.finditer(
        r"<TD[^>]*>\s*(?:<b>)?\s*(?:&nbsp;|\s)*-?\s*([^<]+?)\s*(?:</b>)?\s*</TD>\s*"
        r"<TD[^>]*>\s*(.*?)\s*</TD>",
        html,
        re.I | re.S,
    ):
        label = re.sub(r"\s+", " ", m.group(1)).strip(" \t\r\n\u00a0-")
        raw_val = m.group(2)
        # If value cell contains only an input, skip here (handled as field)
        if re.search(r"<input\b", raw_val, re.I) and not re.search(
            r"[A-Za-z0-9]", re.sub(r"<[^>]+>", "", raw_val)
        ):
            # still try value= attr
            vm = re.search(r"""value\s*=\s*['"]([^'"]*)['"]""", raw_val, re.I)
            value = vm.group(1).strip() if vm else ""
        else:
            value = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw_val)).strip()
        if label and value:
            facts[label] = value
    return facts


def parse_forms(html: str, page_url: str) -> List[FormInfo]:
    forms: List[FormInfo] = []
    for fm in re.finditer(r"<form\b([^>]*)>(.*?)</form>", html, re.I | re.S):
        fa = attrs(fm.group(1))
        body = fm.group(2)
        fields: List[FieldInfo] = []

        for im in re.finditer(r"<input\b([^>]*)/?>", body, re.I):
            a = attrs(im.group(1))
            name = a.get("name", "")
            if not name:
                continue
            fields.append(
                FieldInfo(
                    tag="input",
                    name=name,
                    input_type=a.get("type", "text").lower(),
                    value=a.get("value", ""),
                    checked="checked" in a,
                    disabled="disabled" in a,
                    min=a.get("min", ""),
                    max=a.get("max", ""),
                    step=a.get("step", ""),
                )
            )

        for tm in re.finditer(
            r"<textarea\b([^>]*)>(.*?)</textarea>", body, re.I | re.S
        ):
            a = attrs(tm.group(1))
            name = a.get("name", "")
            if not name:
                continue
            fields.append(
                FieldInfo(
                    tag="textarea",
                    name=name,
                    input_type="textarea",
                    value=tm.group(2).strip(),
                    disabled="disabled" in a,
                )
            )

        for sm in re.finditer(
            r"<select\b([^>]*)>(.*?)</select>", body, re.I | re.S
        ):
            a = attrs(sm.group(1))
            name = a.get("name", "")
            if not name:
                continue
            opts = parse_select(sm.group(2))
            selected_vals = [o["value"] for o in opts if o["selected"]]
            fields.append(
                FieldInfo(
                    tag="select",
                    name=name,
                    input_type="select",
                    value=selected_vals[0] if selected_vals else "",
                    selected=bool(selected_vals),
                    disabled="disabled" in a,
                    options=opts,
                )
            )

        action = fa.get("action", "")
        action_abs = urljoin(page_url, action) if action else page_url
        forms.append(
            FormInfo(
                name=fa.get("name", ""),
                action=action,
                method=fa.get("method", "GET").upper(),
                target=fa.get("target", ""),
                action_abs=action_abs,
                fields=fields,
            )
        )
    return forms


def extract_refs(html: str, base: str) -> Tuple[List[str], List[str]]:
    frames: List[str] = []
    links: List[str] = []
    for m in re.finditer(
        r"""<(?:frame|iframe)\b[^>]*\bsrc\s*=\s*['"]([^'"]+)['"]""",
        html,
        re.I,
    ):
        n = normalize(m.group(1), base)
        if n:
            frames.append(n)
    for m in re.finditer(
        r"""<a\b[^>]*\bhref\s*=\s*['"]([^'"]+)['"]""",
        html,
        re.I,
    ):
        href = m.group(1).strip()
        if href.lower().startswith("javascript:"):
            continue
        n = normalize(href, base)
        if n:
            links.append(n)
    for m in re.finditer(
        r"""location\.href\s*=\s*['"]([^'"]+)['"]""",
        html,
        re.I,
    ):
        n = normalize(m.group(1), base)
        if n:
            links.append(n)
    return frames, links


def page_title(html: str) -> str:
    m = re.search(r'<div class="Title">\s*(.*?)\s*</div>', html, re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def crawl() -> Dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    q: deque[str] = deque(START)
    seen: Set[str] = set()
    pages: Dict[str, PageInfo] = {}
    errors: List[Dict[str, str]] = []

    while q:
        url = q.popleft()
        if url in seen or should_skip(url):
            continue
        seen.add(url)
        time.sleep(SETTLE)
        status, html = fetch(url)
        path = urlparse(url).path.strip("/").replace("/", "_")
        if urlparse(url).query:
            path += "_" + urlparse(url).query.replace("=", "-")[:40]
        (RAW_DIR / f"{path or 'root'}.html").write_text(html, encoding="utf-8")

        if status != 200 or html.startswith("URLError"):
            errors.append({"url": url, "status": str(status), "error": html[:200]})
            continue

        frames, links = extract_refs(html, url)
        forms = parse_forms(html, url)
        title = page_title(html)
        text_facts = extract_text_facts(html)

        pages[url] = PageInfo(
            url=url,
            title=title,
            frames=frames,
            links=links,
            forms=forms,
            text_facts=text_facts,
        )

        for nxt in frames + links:
            if nxt not in seen and not should_skip(nxt):
                q.append(nxt)

    endpoints: Dict[str, Dict] = {}
    for page in pages.values():
        for form in page.forms:
            key = form.action_abs
            if should_skip(key):
                continue
            entry = endpoints.setdefault(
                key,
                {
                    "submit_url": key,
                    "method": form.method,
                    "form_name": form.name,
                    "seen_on_pages": [],
                    "fields": {},
                    "text_facts": {},
                },
            )
            entry["seen_on_pages"].append({"url": page.url, "title": page.title})
            for f in form.fields:
                existing = entry["fields"].get(f.name)
                payload = asdict(f)
                if existing is None:
                    entry["fields"][f.name] = payload
                else:
                    if f.options and not existing.get("options"):
                        existing["options"] = f.options
                    if f.value and not existing.get("value"):
                        existing["value"] = f.value
                    if f.checked:
                        existing["checked"] = True
                        existing["value"] = f.value
            # merge text facts from read pages
            for k, v in page.text_facts.items():
                entry["text_facts"].setdefault(k, v)

    by_section: Dict[str, List[str]] = {}
    for url, page in pages.items():
        parts = urlparse(url).path.strip("/").split("/")
        section = parts[1] if len(parts) > 1 else "SETUP"
        by_section.setdefault(section, []).append(url)

    # Dedicated info extracts
    info_pages = {
        u: asdict(p)
        for u, p in pages.items()
        if any(
            x in u.upper()
            for x in (
                "/NETWORK/",
                "/INFORMATION/",
                "/FIRMWARE/",
                "/IPCONTROL/",
                "/FRIENDLYNAME/",
            )
        )
    }

    result = {
        "host": HOST,
        "mode": "GET-only",
        "excluded": list(SKIP_SUBSTRINGS),
        "page_count": len(pages),
        "endpoint_count": len(endpoints),
        "sections": {k: sorted(v) for k, v in sorted(by_section.items())},
        "pages": {u: asdict(p) for u, p in sorted(pages.items())},
        "endpoints": endpoints,
        "info_pages": info_pages,
        "errors": errors,
    }

    (OUT_DIR / "protocol_map.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )

    slim = []
    for url, ep in sorted(endpoints.items()):
        slim.append(
            {
                "submit_url": url,
                "method": ep["method"],
                "form_name": ep["form_name"],
                "titles": sorted(
                    {p["title"] for p in ep["seen_on_pages"] if p.get("title")}
                ),
                "read_urls": sorted({p["url"] for p in ep["seen_on_pages"]}),
                "field_names": sorted(ep["fields"].keys()),
                "fields": ep["fields"],
                "text_facts": ep.get("text_facts", {}),
            }
        )
    (OUT_DIR / "endpoints.json").write_text(json.dumps(slim, indent=2), encoding="utf-8")

    # Copy into protocol/ for the API
    PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)
    (PROTOCOL_DIR / "protocol_map.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    (PROTOCOL_DIR / "endpoints.json").write_text(
        json.dumps(slim, indent=2), encoding="utf-8"
    )

    print(f"pages={len(pages)} endpoints={len(endpoints)} errors={len(errors)}")
    print(f"wrote {OUT_DIR / 'protocol_map.json'}")
    return result


if __name__ == "__main__":
    crawl()
