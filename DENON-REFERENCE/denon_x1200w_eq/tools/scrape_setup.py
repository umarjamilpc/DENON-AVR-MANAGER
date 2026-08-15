#!/usr/bin/env python3
"""Crawl Denon AVR SETUP web UI and extract every form field (excludes Save/Load)."""

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
START = [
    f"{HOST}/SETUP/f_home.asp",
    f"{HOST}/SETUP/AUDIO/f_audio.asp",
    f"{HOST}/SETUP/VIDEO/f_video.asp",
    f"{HOST}/SETUP/INPUTS/f_inputs.asp",
    f"{HOST}/SETUP/SPEAKERS/f_speakers.asp",
    f"{HOST}/SETUP/NETWORK/f_network.asp",
    f"{HOST}/SETUP/GENERAL/f_general.asp",
]
SKIP_SUBSTRINGS = (
    "/SAVE/",
    "/LOAD/",
    "f_config_save",
    "f_config_load",
    "SAVE/f_",
    "LOAD/f_",
)
OUT_DIR = Path(__file__).resolve().parent / "scrape_out"
RAW_DIR = OUT_DIR / "raw"
TIMEOUT = 20
SETTLE = 0.15


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
    extra: Dict[str, str] = field(default_factory=dict)


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
    notes: List[str] = field(default_factory=list)


def should_skip(url: str) -> bool:
    u = url.upper()
    return any(s.upper() in u for s in SKIP_SUBSTRINGS)


def normalize(url: str, base: str) -> Optional[str]:
    abs_url = urljoin(base, url.strip())
    p = urlparse(abs_url)
    if p.scheme not in ("http", "https"):
        return None
    if p.hostname not in ("192.168.20.50", "localhost"):
        return None
    # strip fragment
    abs_url = urlunparse((p.scheme, p.netloc, p.path, "", p.query, ""))
    if not p.path.upper().startswith("/SETUP"):
        # allow /goform css etc but don't crawl them for forms as pages
        if "/SETUP" not in p.path.upper():
            return None
    if should_skip(abs_url):
        return None
    return abs_url


def fetch(url: str) -> Tuple[int, str]:
    req = Request(
        url,
        headers={"User-Agent": "denon-scraper/1.0", "Accept": "text/html,*/*"},
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


ATTR_RE = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(['"])(.*?)\2""", re.S)


def attrs(tag_html: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in ATTR_RE.finditer(tag_html):
        out[m.group(1).lower()] = m.group(3)
    # boolean attrs
    low = tag_html.lower()
    for b in ("checked", "selected", "disabled", "readonly"):
        if re.search(rf"\b{b}\b", low):
            out[b] = out.get(b, "true")
    return out


def parse_select(block: str) -> List[Dict[str, str]]:
    options = []
    for m in re.finditer(
        r"<option\b([^>]*)>(.*?)</option>",
        block,
        re.I | re.S,
    ):
        a = attrs(m.group(1))
        options.append(
            {
                "value": a.get("value", ""),
                "label": re.sub(r"\s+", " ", m.group(2)).strip(),
                "selected": "selected" in a,
            }
        )
    return options


def parse_forms(html: str, page_url: str) -> List[FormInfo]:
    forms: List[FormInfo] = []
    for fm in re.finditer(r"<form\b([^>]*)>(.*?)</form>", html, re.I | re.S):
        fa = attrs(fm.group(1))
        body = fm.group(2)
        fields: List[FieldInfo] = []

        # inputs
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
                    extra={
                        k: v
                        for k, v in a.items()
                        if k
                        not in {
                            "name",
                            "type",
                            "value",
                            "checked",
                            "disabled",
                            "min",
                            "max",
                            "step",
                        }
                    },
                )
            )

        # textareas
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

        # selects
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
    # also location.href assignments in scripts (rare)
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
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(
        r"""class=['"]Title['"][^>]*>(.*?)</""",
        html,
        re.I | re.S,
    )
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1))
        # cleanup
    m2 = re.search(r'<div class="Title">\s*(.*?)\s*</div>', html, re.I | re.S)
    if m2:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m2.group(1))).strip()
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
        safe = (
            urlparse(url).path.strip("/").replace("/", "_")
            + ("_" + (urlparse(url).query.replace("=", "-")[:40]) if urlparse(url).query else "")
        )
        if not safe:
            safe = "root"
        (RAW_DIR / f"{safe}.html").write_text(html, encoding="utf-8")

        if status != 200 or html.startswith("URLError"):
            errors.append({"url": url, "status": str(status), "error": html[:200]})
            continue

        frames, links = extract_refs(html, url)
        forms = parse_forms(html, url)
        title = page_title(html)
        # prefer Title div
        mtitle = re.search(
            r'<div class="Title">\s*(.*?)\s*</div>', html, re.I | re.S
        )
        if mtitle:
            title = re.sub(
                r"\s+", " ", re.sub(r"<[^>]+>", "", mtitle.group(1))
            ).strip() or title

        notes = []
        if "surrParaForm" in html and not forms:
            notes.append("surrParaForm mentioned but form parse missed")

        pages[url] = PageInfo(
            url=url,
            title=title,
            frames=frames,
            links=links,
            forms=forms,
            notes=notes,
        )

        for nxt in frames + links:
            if nxt not in seen and not should_skip(nxt):
                q.append(nxt)

        # Heuristic: for every f_*.asp frameset under a section, also try
        # sibling d_*.asp / d_right_*.asp / MENU pages if linked via frames already.
        # Additionally, if we see GRAPHICEQ etc menus, crawl list items already via links.

    # Build form catalog keyed by action endpoint
    endpoints: Dict[str, Dict] = {}
    for page in pages.values():
        for form in page.forms:
            key = form.action_abs
            entry = endpoints.setdefault(
                key,
                {
                    "submit_url": key,
                    "method": form.method,
                    "form_name": form.name,
                    "seen_on_pages": [],
                    "fields": {},
                },
            )
            entry["seen_on_pages"].append({"url": page.url, "title": page.title})
            for f in form.fields:
                existing = entry["fields"].get(f.name)
                payload = asdict(f)
                if existing is None:
                    entry["fields"][f.name] = payload
                else:
                    # merge options / values
                    if f.options and not existing.get("options"):
                        existing["options"] = f.options
                    if f.value and not existing.get("value"):
                        existing["value"] = f.value
                    if f.checked:
                        existing["checked"] = True

    # Section index
    by_section: Dict[str, List[str]] = {}
    for url, page in pages.items():
        parts = urlparse(url).path.strip("/").split("/")
        section = parts[1] if len(parts) > 1 else "SETUP"
        by_section.setdefault(section, []).append(url)

    result = {
        "host": HOST,
        "excluded": list(SKIP_SUBSTRINGS),
        "page_count": len(pages),
        "endpoint_count": len(endpoints),
        "sections": {k: sorted(v) for k, v in sorted(by_section.items())},
        "pages": {u: asdict(p) for u, p in sorted(pages.items())},
        "endpoints": endpoints,
        "errors": errors,
    }

    (OUT_DIR / "protocol_map.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )

    # Slim endpoint summary for FastAPI codegen
    slim = []
    for url, ep in sorted(endpoints.items()):
        slim.append(
            {
                "submit_url": url,
                "method": ep["method"],
                "form_name": ep["form_name"],
                "titles": sorted(
                    {
                        p["title"]
                        for p in ep["seen_on_pages"]
                        if p.get("title")
                    }
                ),
                "read_urls": sorted({p["url"] for p in ep["seen_on_pages"]}),
                "field_names": sorted(ep["fields"].keys()),
                "fields": ep["fields"],
            }
        )
    (OUT_DIR / "endpoints.json").write_text(json.dumps(slim, indent=2), encoding="utf-8")

    print(f"pages={len(pages)} endpoints={len(endpoints)} errors={len(errors)}")
    print(f"wrote {OUT_DIR / 'protocol_map.json'}")
    return result


if __name__ == "__main__":
    crawl()
