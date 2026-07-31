"""SQLite persistence for app settings, dashboard, and future local state.

DB path: /data/app.db when the Docker volume exists, else project data/app.db.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

_lock = threading.RLock()
_initialized = False

_WIDGET_SIZES = {"sm", "md", "lg", "xl"}
_SECTION_SIZES = {"full", "half", "third"}
_SHAPES = {"rectangle", "square"}
_SECTION_STACKS = {"horizontal", "vertical"}
_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _norm_color(value: Any, default: str = "") -> str:
    raw = str(value or "").strip()
    if not raw:
        return default
    if not raw.startswith("#"):
        raw = f"#{raw}"
    return raw if _COLOR_RE.match(raw) else default


def _norm_section_stack(value: Any, default: str = "horizontal") -> str:
    v = str(value or default).strip().lower()
    # Migrate legacy section shape values
    if v in {"rectangle", "full", "row"}:
        return "horizontal"
    if v in {"square", "column", "col"}:
        return "vertical"
    return v if v in _SECTION_STACKS else default


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


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r["name"]) for r in rows}


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, column: str, ddl: str
) -> None:
    if column not in _table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Additive migrations for dashboard layout / icons columns."""
    _add_column_if_missing(
        conn, "dashboard_sections", "shape", "shape TEXT NOT NULL DEFAULT 'rectangle'"
    )
    _add_column_if_missing(
        conn, "dashboard_sections", "size", "size TEXT NOT NULL DEFAULT 'full'"
    )
    _add_column_if_missing(
        conn,
        "dashboard_sections",
        "stack",
        "stack TEXT NOT NULL DEFAULT 'horizontal'",
    )
    _add_column_if_missing(
        conn, "dashboard_widgets", "shape", "shape TEXT NOT NULL DEFAULT 'square'"
    )
    _add_column_if_missing(
        conn, "dashboard_widgets", "size", "size TEXT NOT NULL DEFAULT 'md'"
    )
    _add_column_if_missing(
        conn, "dashboard_widgets", "icon_on", "icon_on TEXT NOT NULL DEFAULT ''"
    )
    _add_column_if_missing(
        conn, "dashboard_widgets", "icon_off", "icon_off TEXT NOT NULL DEFAULT ''"
    )
    _add_column_if_missing(
        conn, "dashboard_widgets", "color_on", "color_on TEXT NOT NULL DEFAULT ''"
    )
    _add_column_if_missing(
        conn, "dashboard_widgets", "color_off", "color_off TEXT NOT NULL DEFAULT ''"
    )
    # One-time: map legacy section shapes into stack when still default
    try:
        conn.execute(
            """
            UPDATE dashboard_sections
            SET stack = 'vertical'
            WHERE stack = 'horizontal' AND lower(shape) IN ('square', 'column', 'col')
            """
        )
        conn.execute(
            """
            UPDATE dashboard_sections
            SET stack = 'horizontal'
            WHERE lower(shape) IN ('rectangle', 'full', 'row')
              AND stack NOT IN ('horizontal', 'vertical')
            """
        )
    except sqlite3.Error:
        pass
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
                  shape TEXT NOT NULL DEFAULT 'rectangle',
                  size TEXT NOT NULL DEFAULT 'full',
                  stack TEXT NOT NULL DEFAULT 'horizontal',
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dashboard_widgets (
                  id TEXT PRIMARY KEY,
                  section_id TEXT NOT NULL,
                  control_id TEXT NOT NULL,
                  control_layout TEXT NOT NULL DEFAULT 'less',
                  sort_order INTEGER NOT NULL DEFAULT 0,
                  shape TEXT NOT NULL DEFAULT 'square',
                  size TEXT NOT NULL DEFAULT 'md',
                  icon_on TEXT NOT NULL DEFAULT '',
                  icon_off TEXT NOT NULL DEFAULT '',
                  color_on TEXT NOT NULL DEFAULT '',
                  color_off TEXT NOT NULL DEFAULT '',
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL,
                  FOREIGN KEY (section_id) REFERENCES dashboard_sections(id)
                    ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_dash_widgets_section
                  ON dashboard_widgets(section_id, sort_order);

                CREATE TABLE IF NOT EXISTS custom_icons (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  filename TEXT NOT NULL,
                  mime TEXT,
                  source_url TEXT,
                  created_at REAL NOT NULL
                );
                """
            )
            _migrate_schema(conn)
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
        INSERT INTO dashboard_sections(
          id, title, sort_order, collapsed, shape, size, stack, created_at, updated_at
        ) VALUES (?, ?, 0, 0, 'rectangle', 'full', 'horizontal', ?, ?)
        """,
        (sec_id, "Favourites", now, now),
    )
    seeds = [
        ("pw_power", "less", "mdi:power", "mdi:power-standby", "#e8eef2", "#3a4248"),
        ("mu_mute", "less", "mdi:volume-off", "mdi:volume-high", "#e8eef2", "#3a4248"),
        ("si_select", "less", "mdi:import", "mdi:import", "#e8eef2", "#3a4248"),
        ("ms_select", "less", "mdi:surround-sound", "mdi:surround-sound", "#e8eef2", "#3a4248"),
    ]
    for i, (cid, layout, ion, ioff, con, coff) in enumerate(seeds):
        conn.execute(
            """
            INSERT INTO dashboard_widgets(
              id, section_id, control_id, control_layout, sort_order,
              shape, size, icon_on, icon_off, color_on, color_off,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'square', 'md', ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), sec_id, cid, layout, i, ion, ioff, con, coff, now, now),
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


def _norm_shape(value: Any, default: str = "rectangle") -> str:
    v = str(value or default).strip().lower()
    return v if v in _SHAPES else default


def _norm_widget_size(value: Any, default: str = "md") -> str:
    v = str(value or default).strip().lower()
    return v if v in _WIDGET_SIZES else default


def _norm_section_size(value: Any, default: str = "full") -> str:
    v = str(value or default).strip().lower()
    return v if v in _SECTION_SIZES else default


def _widget_row(w: sqlite3.Row) -> Dict[str, Any]:
    keys = w.keys()
    return {
        "id": w["id"],
        "section_id": w["section_id"],
        "control_id": w["control_id"],
        "control_layout": w["control_layout"],
        "sort_order": int(w["sort_order"]),
        "shape": _norm_shape(w["shape"] if "shape" in keys else "square", "square"),
        "size": _norm_widget_size(w["size"] if "size" in keys else "md"),
        "icon_on": str(w["icon_on"] if "icon_on" in keys else ""),
        "icon_off": str(w["icon_off"] if "icon_off" in keys else ""),
        "color_on": _norm_color(w["color_on"] if "color_on" in keys else ""),
        "color_off": _norm_color(w["color_off"] if "color_off" in keys else ""),
    }


def _section_stack_from_row(s: sqlite3.Row) -> str:
    keys = s.keys()
    if "stack" in keys and s["stack"]:
        return _norm_section_stack(s["stack"])
    return _norm_section_stack(s["shape"] if "shape" in keys else "horizontal")


def load_dashboard() -> Dict[str, Any]:
    init_db()
    with _lock, connect() as conn:
        sections = conn.execute(
            """
            SELECT id, title, sort_order, collapsed, shape, size, stack,
                   created_at, updated_at
            FROM dashboard_sections
            ORDER BY sort_order ASC, title ASC
            """
        ).fetchall()
        widgets = conn.execute(
            """
            SELECT id, section_id, control_id, control_layout, sort_order,
                   shape, size, icon_on, icon_off, color_on, color_off,
                   created_at, updated_at
            FROM dashboard_widgets
            ORDER BY sort_order ASC
            """
        ).fetchall()
    by_sec: Dict[str, List[Dict[str, Any]]] = {}
    for w in widgets:
        by_sec.setdefault(str(w["section_id"]), []).append(_widget_row(w))
    return {
        "sections": [
            {
                "id": s["id"],
                "title": s["title"],
                "sort_order": int(s["sort_order"]),
                "collapsed": bool(s["collapsed"]),
                "stack": _section_stack_from_row(s),
                "size": _norm_section_size(s["size"] if "size" in s.keys() else "full"),
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
            stack = _norm_section_stack(sec.get("stack") or sec.get("shape"))
            size = _norm_section_size(sec.get("size"))
            conn.execute(
                """
                INSERT INTO dashboard_sections(
                  id, title, sort_order, collapsed, shape, size, stack,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    title,
                    int(sec.get("sort_order", si)),
                    collapsed,
                    "rectangle",
                    size,
                    stack,
                    now,
                    now,
                ),
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
                      shape, size, icon_on, icon_off, color_on, color_off,
                      created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        wid,
                        sid,
                        cid,
                        layout,
                        int(w.get("sort_order", wi)),
                        _norm_shape(w.get("shape"), "square"),
                        _norm_widget_size(w.get("size")),
                        str(w.get("icon_on") or ""),
                        str(w.get("icon_off") or ""),
                        _norm_color(w.get("color_on")),
                        _norm_color(w.get("color_off")),
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
              id, title, sort_order, collapsed, shape, size, stack,
              created_at, updated_at
            ) VALUES (?, ?, ?, 0, 'rectangle', 'full', 'horizontal', ?, ?)
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


def update_section(section_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    now = time.time()
    sets: List[str] = []
    vals: List[Any] = []
    if "title" in fields and fields["title"] is not None:
        sets.append("title = ?")
        vals.append(str(fields["title"]).strip() or "Section")
    if "stack" in fields and fields["stack"] is not None:
        sets.append("stack = ?")
        vals.append(_norm_section_stack(fields["stack"]))
    elif "shape" in fields and fields["shape"] is not None:
        # Legacy: section shape mapped to stack
        sets.append("stack = ?")
        vals.append(_norm_section_stack(fields["shape"]))
    if "size" in fields and fields["size"] is not None:
        sets.append("size = ?")
        vals.append(_norm_section_size(fields["size"]))
    if "collapsed" in fields and fields["collapsed"] is not None:
        sets.append("collapsed = ?")
        vals.append(1 if fields["collapsed"] else 0)
    if not sets:
        return load_dashboard()
    sets.append("updated_at = ?")
    vals.append(now)
    vals.append(section_id)
    with _lock, connect() as conn:
        conn.execute(
            f"UPDATE dashboard_sections SET {', '.join(sets)} WHERE id = ?",
            vals,
        )
    return load_dashboard()


def rename_section(section_id: str, title: str) -> Dict[str, Any]:
    return update_section(section_id, {"title": title})


def add_widget(
    section_id: str,
    control_id: str,
    control_layout: str = "less",
    *,
    shape: str = "square",
    size: str = "md",
    icon_on: str = "",
    icon_off: str = "",
    color_on: str = "",
    color_off: str = "",
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
              shape, size, icon_on, icon_off, color_on, color_off,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                section_id,
                cid,
                layout,
                order,
                _norm_shape(shape, "square"),
                _norm_widget_size(size),
                str(icon_on or ""),
                str(icon_off or ""),
                _norm_color(color_on),
                _norm_color(color_off),
                now,
                now,
            ),
        )
    return load_dashboard()


def update_widget(widget_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    now = time.time()
    sets: List[str] = []
    vals: List[Any] = []
    if "shape" in fields and fields["shape"] is not None:
        sets.append("shape = ?")
        vals.append(_norm_shape(fields["shape"], "square"))
    if "size" in fields and fields["size"] is not None:
        sets.append("size = ?")
        vals.append(_norm_widget_size(fields["size"]))
    if "icon_on" in fields and fields["icon_on"] is not None:
        sets.append("icon_on = ?")
        vals.append(str(fields["icon_on"]))
    if "icon_off" in fields and fields["icon_off"] is not None:
        sets.append("icon_off = ?")
        vals.append(str(fields["icon_off"]))
    if "color_on" in fields and fields["color_on"] is not None:
        sets.append("color_on = ?")
        vals.append(_norm_color(fields["color_on"]))
    if "color_off" in fields and fields["color_off"] is not None:
        sets.append("color_off = ?")
        vals.append(_norm_color(fields["color_off"]))
    if "control_layout" in fields and fields["control_layout"] is not None:
        layout = str(fields["control_layout"]).lower()
        layout = "more" if layout in {"more", "ungrouped"} else "less"
        sets.append("control_layout = ?")
        vals.append(layout)
    if not sets:
        return load_dashboard()
    sets.append("updated_at = ?")
    vals.append(now)
    vals.append(widget_id)
    with _lock, connect() as conn:
        conn.execute(
            f"UPDATE dashboard_widgets SET {', '.join(sets)} WHERE id = ?",
            vals,
        )
    return load_dashboard()


def delete_widget(widget_id: str) -> Dict[str, Any]:
    init_db()
    with _lock, connect() as conn:
        conn.execute("DELETE FROM dashboard_widgets WHERE id = ?", (widget_id,))
    return load_dashboard()
