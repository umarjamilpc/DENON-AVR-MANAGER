"""Custom icon storage for dashboard widgets (file upload or URL fetch → local disk)."""

from __future__ import annotations

import mimetypes
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from . import db

_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}
_MAX_BYTES = 2 * 1024 * 1024  # 2 MiB


def icons_dir() -> Path:
    path = db.data_dir() / "icons"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_ext(name: str, content_type: str = "") -> str:
    ext = Path(name or "").suffix.lower()
    if ext in _ALLOWED_EXT:
        return ext
    guessed = mimetypes.guess_extension((content_type or "").split(";")[0].strip()) or ""
    if guessed == ".jpe":
        guessed = ".jpg"
    if guessed in _ALLOWED_EXT:
        return guessed
    return ".png"


def _ensure_icons_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS custom_icons (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          filename TEXT NOT NULL,
          mime TEXT,
          source_url TEXT,
          created_at REAL NOT NULL
        )
        """
    )


def list_icons() -> List[Dict[str, Any]]:
    db.init_db()
    with db._lock, db.connect() as conn:
        _ensure_icons_table(conn)
        rows = conn.execute(
            """
            SELECT id, name, filename, mime, source_url, created_at
            FROM custom_icons ORDER BY created_at DESC
            """
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "name": r["name"],
                "filename": r["filename"],
                "mime": r["mime"],
                "source_url": r["source_url"],
                "created_at": r["created_at"],
                "url": f"/icons/{r['filename']}",
                "ref": f"custom:{r['id']}",
            }
        )
    return out


def save_icon_bytes(
    data: bytes,
    *,
    name: str = "icon",
    filename_hint: str = "",
    content_type: str = "",
    source_url: Optional[str] = None,
) -> Dict[str, Any]:
    if not data:
        raise ValueError("empty icon data")
    if len(data) > _MAX_BYTES:
        raise ValueError(f"icon too large (max {_MAX_BYTES} bytes)")
    db.init_db()
    icon_id = str(uuid.uuid4())
    ext = _safe_ext(filename_hint or name, content_type)
    filename = f"{icon_id}{ext}"
    path = icons_dir() / filename
    path.write_bytes(data)
    mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    display = (name or Path(filename_hint).stem or "icon").strip()[:80] or "icon"
    now = time.time()
    with db._lock, db.connect() as conn:
        _ensure_icons_table(conn)
        conn.execute(
            """
            INSERT INTO custom_icons(id, name, filename, mime, source_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (icon_id, display, filename, mime, source_url, now),
        )
    return {
        "id": icon_id,
        "name": display,
        "filename": filename,
        "mime": mime,
        "source_url": source_url,
        "created_at": now,
        "url": f"/icons/{filename}",
        "ref": f"custom:{icon_id}",
    }


def save_icon_from_url(url: str, name: str = "") -> Dict[str, Any]:
    raw = (url or "").strip()
    if not re.match(r"^https?://", raw, re.I):
        raise ValueError("url must start with http:// or https://")
    req = Request(
        raw,
        headers={"User-Agent": "DENON-AVR-MANAGER/1.0 (icon-fetch)"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            data = resp.read(_MAX_BYTES + 1)
            ctype = resp.headers.get("Content-Type", "")
            # Prefer Content-Disposition / URL path for extension
            hint = raw.split("?")[0].rstrip("/").split("/")[-1]
    except (URLError, HTTPError, TimeoutError, OSError) as e:
        raise ValueError(f"failed to fetch icon: {e}") from e
    if len(data) > _MAX_BYTES:
        raise ValueError(f"icon too large (max {_MAX_BYTES} bytes)")
    display = name.strip() if name else Path(hint).stem or "icon"
    return save_icon_bytes(
        data,
        name=display,
        filename_hint=hint,
        content_type=ctype,
        source_url=raw,
    )


def delete_icon(icon_id: str) -> None:
    db.init_db()
    with db._lock, db.connect() as conn:
        _ensure_icons_table(conn)
        row = conn.execute(
            "SELECT filename FROM custom_icons WHERE id = ?", (icon_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"unknown icon: {icon_id}")
        conn.execute("DELETE FROM custom_icons WHERE id = ?", (icon_id,))
        filename = row["filename"]
    path = icons_dir() / filename
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


def resolve_icon_ref(ref: str) -> Optional[Dict[str, Any]]:
    """Return {type, class|url, name} for mdi:xxx or custom:uuid."""
    raw = (ref or "").strip()
    if not raw:
        return None
    if raw.startswith("mdi:"):
        name = raw[4:].strip().lstrip("-")
        if not name:
            return None
        css = name if name.startswith("mdi-") else f"mdi-{name}"
        return {"type": "mdi", "class": css, "ref": f"mdi:{name.replace('mdi-', '')}"}
    if raw.startswith("custom:"):
        icon_id = raw.split(":", 1)[1].strip()
        for item in list_icons():
            if item["id"] == icon_id:
                return {
                    "type": "custom",
                    "url": item["url"],
                    "name": item["name"],
                    "ref": item["ref"],
                }
        return None
    # bare mdi name
    if re.match(r"^mdi-[\w-]+$", raw) or re.match(r"^[\w-]+$", raw):
        name = raw if raw.startswith("mdi-") else f"mdi-{raw}"
        return {"type": "mdi", "class": name, "ref": f"mdi:{name[4:]}"}
    return None
