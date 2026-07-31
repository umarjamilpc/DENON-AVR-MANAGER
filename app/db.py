"""SQLite persistence for app settings, dashboard, and future local state.

DB path: /data/app.db when the Docker volume exists, else project data/app.db.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

_lock = threading.RLock()
_initialized = False


def data_dir() -> Path:
    if Path("/data").is_dir():
        return Path("/data")
    return Path(__file__).resolve().parents[1] / "data"


def db_path() -> Path:
    return data_dir() / "app.db"


def legacy_settings_json_path() -> Path:
    return data_dir() / "app-settings.json"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and migrate legacy JSON settings once."""
    global _initialized
    with _lock:
        if _initialized:
            return
        with connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dashboard_sections (
                  id TEXT PRIMARY KEY,
                  title TEXT NOT NULL,
                  sort_order INTEGER NOT NULL DEFAULT 0,
                  collapsed INTEGER NOT NULL DEFAULT 0,
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dashboard_widgets (
                  id TEXT PRIMARY KEY,
                  section_id TEXT NOT NULL,
                  control_id TEXT NOT NULL,
                  control_layout TEXT NOT NULL DEFAULT 'less',
                  sort_order INTEGER NOT NULL DEFAULT 0,
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL,
                  FOREIGN KEY (section_id) REFERENCES dashboard_sections(id)
                    ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_dash_widgets_section
                  ON dashboard_widgets(section_id, sort_order);
                """
            )
            _migrate_settings_from_json(conn)
            _ensure_default_dashboard(conn)
        _initialized = True


def _migrate_settings_from_json(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT COUNT(*) AS n FROM app_settings").fetchone()
    if row and int(row["n"]) > 0:
        return
    path = legacy_settings_json_path()
    if not path.is_file():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(raw, dict):
        return
    for key, value in raw.items():
        conn.execute(
            "INSERT OR REPLACE INTO app_settings(key, value) VALUES (?, ?)",
            (str(key), json.dumps(value)),
        )


def _ensure_default_dashboard(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT COUNT(*) AS n FROM dashboard_sections").fetchone()
    if row and int(row["n"]) > 0:
        return
    now = time.time()
    sec_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO dashboard_sections(id, title, sort_order, collapsed, created_at, updated_at)
        VALUES (?, ?, 0, 0, ?, ?)
        """,
        (sec_id, "Favourites", now, now),
    )
    # Seed a few useful widgets (less-layout toggles / enums)
    seeds = [
        ("pw_power", "less"),
        ("mu_mute", "less"),
        ("si_select", "less"),
        ("ms_select", "less"),
    ]
    for i, (cid, layout) in enumerate(seeds):
        conn.execute(
            """
            INSERT INTO dashboard_widgets(
              id, section_id, control_id, control_layout, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), sec_id, cid, layout, i, now, now),
        )


def get_setting_rows() -> Dict[str, Any]:
    init_db()
    with _lock, connect() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    out: Dict[str, Any] = {}
    for row in rows:
        try:
            out[str(row["key"])] = json.loads(row["value"])
        except json.JSONDecodeError:
            out[str(row["key"])] = row["value"]
    return out


def set_setting_rows(settings: Dict[str, Any]) -> None:
    init_db()
    with _lock, connect() as conn:
        conn.execute("DELETE FROM app_settings")
        for key, value in settings.items():
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES (?, ?)",
                (str(key), json.dumps(value)),
            )


def new_id() -> str:
    return str(uuid.uuid4())


def load_dashboard() -> Dict[str, Any]:
    init_db()
    with _lock, connect() as conn:
        sections = conn.execute(
            """
            SELECT id, title, sort_order, collapsed, created_at, updated_at
            FROM dashboard_sections
            ORDER BY sort_order ASC, title ASC
            """
        ).fetchall()
        widgets = conn.execute(
            """
            SELECT id, section_id, control_id, control_layout, sort_order,
                   created_at, updated_at
            FROM dashboard_widgets
            ORDER BY sort_order ASC
            """
        ).fetchall()
    by_sec: Dict[str, List[Dict[str, Any]]] = {}
    for w in widgets:
        by_sec.setdefault(str(w["section_id"]), []).append(
            {
                "id": w["id"],
                "section_id": w["section_id"],
                "control_id": w["control_id"],
                "control_layout": w["control_layout"],
                "sort_order": int(w["sort_order"]),
            }
        )
    return {
        "sections": [
            {
                "id": s["id"],
                "title": s["title"],
                "sort_order": int(s["sort_order"]),
                "collapsed": bool(s["collapsed"]),
                "widgets": by_sec.get(str(s["id"]), []),
            }
            for s in sections
        ]
    }


def replace_dashboard(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Replace entire dashboard layout (used by drag-drop save)."""
    init_db()
    sections_in = payload.get("sections") or []
    if not isinstance(sections_in, list):
        raise ValueError("sections must be a list")
    now = time.time()
    with _lock, connect() as conn:
        conn.execute("DELETE FROM dashboard_widgets")
        conn.execute("DELETE FROM dashboard_sections")
        for si, sec in enumerate(sections_in):
            if not isinstance(sec, dict):
                continue
            sid = str(sec.get("id") or new_id())
            title = str(sec.get("title") or "Section").strip() or "Section"
            collapsed = 1 if sec.get("collapsed") else 0
            conn.execute(
                """
                INSERT INTO dashboard_sections(
                  id, title, sort_order, collapsed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sid, title, int(sec.get("sort_order", si)), collapsed, now, now),
            )
            widgets = sec.get("widgets") or []
            if not isinstance(widgets, list):
                continue
            for wi, w in enumerate(widgets):
                if not isinstance(w, dict):
                    continue
                cid = str(w.get("control_id") or "").strip()
                if not cid:
                    continue
                layout = str(w.get("control_layout") or "less").strip().lower()
                if layout not in {"less", "more"}:
                    layout = "less"
                wid = str(w.get("id") or new_id())
                conn.execute(
                    """
                    INSERT INTO dashboard_widgets(
                      id, section_id, control_id, control_layout, sort_order,
                      created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        wid,
                        sid,
                        cid,
                        layout,
                        int(w.get("sort_order", wi)),
                        now,
                        now,
                    ),
                )
    return load_dashboard()


def add_section(title: str = "New section") -> Dict[str, Any]:
    init_db()
    now = time.time()
    sid = new_id()
    with _lock, connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS m FROM dashboard_sections"
        ).fetchone()
        order = int(row["m"]) + 1 if row else 0
        conn.execute(
            """
            INSERT INTO dashboard_sections(
              id, title, sort_order, collapsed, created_at, updated_at
            ) VALUES (?, ?, ?, 0, ?, ?)
            """,
            (sid, (title or "New section").strip() or "New section", order, now, now),
        )
    return load_dashboard()


def delete_section(section_id: str) -> Dict[str, Any]:
    init_db()
    with _lock, connect() as conn:
        conn.execute(
            "DELETE FROM dashboard_widgets WHERE section_id = ?", (section_id,)
        )
        conn.execute("DELETE FROM dashboard_sections WHERE id = ?", (section_id,))
    return load_dashboard()


def rename_section(section_id: str, title: str) -> Dict[str, Any]:
    init_db()
    now = time.time()
    with _lock, connect() as conn:
        conn.execute(
            """
            UPDATE dashboard_sections
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            ((title or "").strip() or "Section", now, section_id),
        )
    return load_dashboard()


def add_widget(
    section_id: str, control_id: str, control_layout: str = "less"
) -> Dict[str, Any]:
    init_db()
    now = time.time()
    layout = "more" if str(control_layout).lower() in {"more", "ungrouped"} else "less"
    cid = (control_id or "").strip()
    if not cid:
        raise ValueError("control_id required")
    with _lock, connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM dashboard_sections WHERE id = ?", (section_id,)
        ).fetchone()
        if not exists:
            raise KeyError(f"unknown section: {section_id}")
        row = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), -1) AS m
            FROM dashboard_widgets WHERE section_id = ?
            """,
            (section_id,),
        ).fetchone()
        order = int(row["m"]) + 1 if row else 0
        conn.execute(
            """
            INSERT INTO dashboard_widgets(
              id, section_id, control_id, control_layout, sort_order,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id(), section_id, cid, layout, order, now, now),
        )
    return load_dashboard()


def delete_widget(widget_id: str) -> Dict[str, Any]:
    init_db()
    with _lock, connect() as conn:
        conn.execute("DELETE FROM dashboard_widgets WHERE id = ?", (widget_id,))
    return load_dashboard()
