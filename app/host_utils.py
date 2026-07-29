"""AVR host helpers — any Denon on the LAN, not just the scrape IP."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse


_IP_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d?\d)$"
)
_HOST_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


def normalize_host(value: str) -> str:
    """Accept `192.168.1.10`, `http://192.168.1.10`, host:port → `http://...`."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Host is empty")
    if "://" not in raw:
        raw = "http://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https AVR hosts are supported")
    if not parsed.hostname:
        raise ValueError("Missing hostname / IP")
    host = parsed.hostname
    # Allow IPs and local DNS names (denon.local etc.)
    if not (_IP_RE.match(host) or _HOST_RE.match(host)):
        raise ValueError(f"Invalid host: {host}")
    netloc = parsed.netloc  # may include port
    return urlunparse((parsed.scheme, netloc, "", "", "", "")).rstrip("/")


def host_label(base: str) -> str:
    p = urlparse(base if "://" in base else f"http://{base}")
    return p.netloc or p.path


def rewrite_url(url: str, base: str) -> str:
    """Point a scraped absolute URL (or /SETUP path) at the current AVR base."""
    base = normalize_host(base)
    if not url:
        return base
    if url.startswith("/"):
        return f"{base}{url}"
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.path:
        return f"{base}{parsed.path}"
    if parsed.path.startswith("/"):
        return f"{base}{parsed.path}"
    return f"{base}/{url.lstrip('/')}"


def url_path(url: str) -> str:
    """Strip scheme/host — API responses never expose DENON_HOST."""
    if not url:
        return ""
    if url.startswith("/"):
        return url
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def rewrite_endpoint(item: Dict[str, Any], base: str) -> Dict[str, Any]:
    """Rewrite endpoint URLs for the configured AVR as path-only (no host leak)."""
    _ = base  # host stays in DENON_HOST / client; URLs in JSON are paths
    out = dict(item)
    if out.get("submit_url"):
        out["submit_url"] = url_path(out["submit_url"])
    reads: List[str] = list(out.get("read_urls") or [])
    out["read_urls"] = [url_path(u) for u in reads]
    return out


def scrub_host_urls(data: Any) -> Any:
    """Recursively convert absolute http(s) URLs in API payloads to paths."""
    if isinstance(data, dict):
        return {k: scrub_host_urls(v) for k, v in data.items()}
    if isinstance(data, list):
        return [scrub_host_urls(v) for v in data]
    if isinstance(data, str) and data.startswith(("http://", "https://")):
        return url_path(data)
    return data


def resolve_request_host(
    *,
    query_host: Optional[str],
    header_host: Optional[str],
    default_base: str,
) -> str:
    chosen = (query_host or header_host or default_base or "").strip()
    return normalize_host(chosen)
