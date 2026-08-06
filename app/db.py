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
_CONTROL_UI = {"auto", "popup", "inline"}
_WIDGET_SIZE_TO_PX = {
    "sm": (96, 96),
    "md": (120, 120),
    "lg": (180, 140),
    "xl": (280, 160),
}
_SECTION_SIZE_TO_PX = {
    "full": (0, 0),
    "half": (480, 0),
    "third": (320, 0),
}
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


def _migrate_layouts(conn: sqlite3.Connection) -> None:
    """Ensure every section belongs to a layout; create empty-ready layout rows."""
    n_layouts = conn.execute(
        "SELECT COUNT(*) AS n FROM dashboard_layouts"
    ).fetchone()
    if n_layouts and int(n_layouts["n"]) > 0:
        # Attach any orphan sections to a new horizontal layout
        orphans = conn.execute(
            """
            SELECT id, size, sort_order FROM dashboard_sections
            WHERE layout_id IS NULL OR layout_id = ''
            ORDER BY sort_order ASC, title ASC
            """
        ).fetchall()
        if orphans:
            _assign_sections_to_layouts(conn, orphans)
        return

    sections = conn.execute(
        """
        SELECT id, size, sort_order FROM dashboard_sections
        ORDER BY sort_order ASC, title ASC
        """
    ).fetchall()
    if not sections:
        now = time.time()
        lid = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO dashboard_layouts(id, stack, sort_order, created_at, updated_at)
            VALUES (?, 'horizontal', 0, ?, ?)
            """,
            (lid, now, now),
        )
        return
    _assign_sections_to_layouts(conn, sections)


def _assign_sections_to_layouts(
    conn: sqlite3.Connection, sections: List[sqlite3.Row]
) -> None:
    """Group consecutive non-full sections into horizontal layouts; full = own row."""
    now = time.time()
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) AS m FROM dashboard_layouts"
    ).fetchone()
    layout_order = int(row["m"]) + 1 if row else 0
    i = 0
    while i < len(sections):
        size = _norm_section_size(sections[i]["size"] if "size" in sections[i].keys() else "full")
        if size == "full":
            lid = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO dashboard_layouts(id, stack, sort_order, created_at, updated_at)
                VALUES (?, 'vertical', ?, ?, ?)
                """,
                (lid, layout_order, now, now),
            )
            conn.execute(
                "UPDATE dashboard_sections SET layout_id = ? WHERE id = ?",
                (lid, sections[i]["id"]),
            )
            layout_order += 1
            i += 1
            continue
        lid = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO dashboard_layouts(id, stack, sort_order, created_at, updated_at)
            VALUES (?, 'horizontal', ?, ?, ?)
            """,
            (lid, layout_order, now, now),
        )
        while i < len(sections):
            sz = _norm_section_size(
                sections[i]["size"] if "size" in sections[i].keys() else "full"
            )
            if sz == "full":
                break
            conn.execute(
                "UPDATE dashboard_sections SET layout_id = ? WHERE id = ?",
                (lid, sections[i]["id"]),
            )
            i += 1
        layout_order += 1


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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dashboard_layouts (
          id TEXT PRIMARY KEY,
          stack TEXT NOT NULL DEFAULT 'horizontal',
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_at REAL NOT NULL,
          updated_at REAL NOT NULL
        )
        """
    )
    _add_column_if_missing(
        conn, "dashboard_sections", "layout_id", "layout_id TEXT"
    )
    _add_column_if_missing(
        conn, "dashboard_sections", "width_px", "width_px INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing(
        conn, "dashboard_sections", "height_px", "height_px INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing(
        conn, "dashboard_widgets", "width_px", "width_px INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing(
        conn, "dashboard_widgets", "height_px", "height_px INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing(
        conn,
        "dashboard_widgets",
        "control_ui",
        "control_ui TEXT NOT NULL DEFAULT 'auto'",
    )
    _add_column_if_missing(
        conn,
        "dashboard_widgets",
        "card_mod",
        "card_mod TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        conn,
        "dashboard_sections",
        "card_mod",
        "card_mod TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        conn,
        "dashboard_widgets",
        "custom_name",
        "custom_name TEXT NOT NULL DEFAULT ''",
    )
    _migrate_px_sizes(conn)
    _migrate_layouts(conn)

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


def _norm_px(value: Any, default: int = 0) -> int:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(0, min(4000, n))


def _norm_sort_order(value: Any, default: int = 0) -> int:
    """Coerce sort_order; YAML null/missing values fall back to index."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm_control_ui(value: Any, default: str = "auto") -> str:
    v = str(value or default).strip().lower()
    return v if v in _CONTROL_UI else default


def _norm_card_mod(value: Any) -> str:
    """Store card_mod as JSON text: {"style": "..."}. Empty string if none."""
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ""
        if s.startswith("{"):
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    style = obj.get("style") or ""
                    if isinstance(style, dict):
                        style = "\n".join(
                            f"{k} {{\n{v}\n}}" for k, v in style.items()
                        )
                    style_s = str(style).strip()
                    return (
                        json.dumps({"style": style_s}, ensure_ascii=False)
                        if style_s
                        else ""
                    )
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return json.dumps({"style": s}, ensure_ascii=False)
    if isinstance(value, dict):
        style = value.get("style") or ""
        if isinstance(style, dict):
            style = "\n".join(f"{k} {{\n{v}\n}}" for k, v in style.items())
        style_s = str(style).strip()
        return (
            json.dumps({"style": style_s}, ensure_ascii=False) if style_s else ""
        )
    return ""


def _card_mod_obj(raw: Any) -> Optional[Dict[str, str]]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            style = str(obj.get("style") or "").strip()
            return {"style": style} if style else None
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    return {"style": text}


def _migrate_px_sizes(conn: sqlite3.Connection) -> None:
    """One-time: map legacy size tokens into width_px/height_px when still 0."""
    try:
        for token, (w, h) in _WIDGET_SIZE_TO_PX.items():
            conn.execute(
                """
                UPDATE dashboard_widgets
                SET width_px = ?, height_px = ?
                WHERE (width_px IS NULL OR width_px = 0)
                  AND (height_px IS NULL OR height_px = 0)
                  AND lower(size) = ?
                """,
                (w, h, token),
            )
        # Default remaining widgets
        conn.execute(
            """
            UPDATE dashboard_widgets
            SET width_px = 120, height_px = 120
            WHERE (width_px IS NULL OR width_px = 0)
              AND (height_px IS NULL OR height_px = 0)
            """
        )
        for token, (w, h) in _SECTION_SIZE_TO_PX.items():
            conn.execute(
                """
                UPDATE dashboard_sections
                SET width_px = ?, height_px = ?
                WHERE (width_px IS NULL OR width_px = 0)
                  AND (height_px IS NULL OR height_px = 0)
                  AND lower(size) = ?
                """,
                (w, h, token),
            )
    except sqlite3.Error:
        pass


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
    width_px = _norm_px(w["width_px"] if "width_px" in keys else 0)
    height_px = _norm_px(w["height_px"] if "height_px" in keys else 0)
    if width_px <= 0 and height_px <= 0:
        width_px, height_px = _WIDGET_SIZE_TO_PX.get(
            _norm_widget_size(w["size"] if "size" in keys else "md"),
            (120, 120),
        )
    return {
        "id": w["id"],
        "section_id": w["section_id"],
        "control_id": w["control_id"],
        "control_layout": w["control_layout"],
        "sort_order": int(w["sort_order"]),
        "shape": _norm_shape(w["shape"] if "shape" in keys else "square", "square"),
        "size": _norm_widget_size(w["size"] if "size" in keys else "md"),
        "width_px": width_px,
        "height_px": height_px,
        "control_ui": _norm_control_ui(
            w["control_ui"] if "control_ui" in keys else "auto"
        ),
        "icon_on": str(w["icon_on"] if "icon_on" in keys else ""),
        "icon_off": str(w["icon_off"] if "icon_off" in keys else ""),
        "color_on": _norm_color(w["color_on"] if "color_on" in keys else ""),
        "color_off": _norm_color(w["color_off"] if "color_off" in keys else ""),
        "custom_name": str(w["custom_name"] if "custom_name" in keys else "").strip(),
        "card_mod": _card_mod_obj(w["card_mod"] if "card_mod" in keys else ""),
    }


def _section_stack_from_row(s: sqlite3.Row) -> str:
    keys = s.keys()
    if "stack" in keys and s["stack"]:
        return _norm_section_stack(s["stack"])
    return _norm_section_stack(s["shape"] if "shape" in keys else "horizontal")


def load_dashboard() -> Dict[str, Any]:
    init_db()
    with _lock, connect() as conn:
        _migrate_schema(conn)
        layouts = conn.execute(
            """
            SELECT id, stack, sort_order, created_at, updated_at
            FROM dashboard_layouts
            ORDER BY sort_order ASC
            """
        ).fetchall()
        sections = conn.execute(
            """
            SELECT id, title, sort_order, collapsed, shape, size, stack,
                   layout_id, width_px, height_px, card_mod, created_at, updated_at
            FROM dashboard_sections
            ORDER BY sort_order ASC, title ASC
            """
        ).fetchall()
        widgets = conn.execute(
            """
            SELECT id, section_id, control_id, control_layout, sort_order,
                   shape, size, icon_on, icon_off, color_on, color_off,
                   width_px, height_px, control_ui, card_mod, custom_name,
                   created_at, updated_at
            FROM dashboard_widgets
            ORDER BY sort_order ASC
            """
        ).fetchall()
    by_sec: Dict[str, List[Dict[str, Any]]] = {}
    for w in widgets:
        by_sec.setdefault(str(w["section_id"]), []).append(_widget_row(w))
    sections_out = []
    for s in sections:
        keys = s.keys()
        width_px = _norm_px(s["width_px"] if "width_px" in keys else 0)
        height_px = _norm_px(s["height_px"] if "height_px" in keys else 0)
        size_token = _norm_section_size(s["size"] if "size" in keys else "full")
        if width_px <= 0 and height_px <= 0:
            width_px, height_px = _SECTION_SIZE_TO_PX.get(size_token, (0, 0))
        sections_out.append(
            {
                "id": s["id"],
                "title": s["title"],
                "sort_order": int(s["sort_order"]),
                "collapsed": bool(s["collapsed"]),
                "stack": "horizontal",
                "size": size_token,
                "width_px": width_px,
                "height_px": height_px,
                "layout_id": str(s["layout_id"] or "") if "layout_id" in keys else "",
                "card_mod": _card_mod_obj(
                    s["card_mod"] if "card_mod" in keys else ""
                ),
                "widgets": by_sec.get(str(s["id"]), []),
            }
        )
    by_layout: Dict[str, List[Dict[str, Any]]] = {}
    for sec in sections_out:
        lid = sec.get("layout_id") or ""
        by_layout.setdefault(lid, []).append(sec)
    layouts_out = [
        {
            "id": ly["id"],
            "stack": _norm_section_stack(ly["stack"]),
            "sort_order": int(ly["sort_order"]),
            "sections": by_layout.get(str(ly["id"]), []),
        }
        for ly in layouts
    ]
    # Orphans (no layout) — wrap as synthetic horizontal layouts for API consumers
    orphans = by_layout.get("", [])
    if orphans:
        layouts_out.append(
            {
                "id": "",
                "stack": "horizontal",
                "sort_order": len(layouts_out),
                "sections": orphans,
            }
        )
    return {"layouts": layouts_out, "sections": sections_out}


def replace_dashboard(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Replace entire dashboard layout (used by drag-drop save)."""
    init_db()
    layouts_in = payload.get("layouts")
    sections_in = payload.get("sections") or []
    if layouts_in is not None and not isinstance(layouts_in, list):
        raise ValueError("layouts must be a list")
    if not isinstance(sections_in, list):
        raise ValueError("sections must be a list")
    flat_layouts: List[Dict[str, Any]] = []
    if isinstance(layouts_in, list) and layouts_in:
        sections_in = []
        for li, ly in enumerate(layouts_in):
            if not isinstance(ly, dict):
                continue
            lid = str(ly.get("id") or new_id())
            flat_layouts.append(
                {
                    "id": lid,
                    "stack": _norm_section_stack(ly.get("stack")),
                    "sort_order": _norm_sort_order(ly.get("sort_order"), li),
                }
            )
            for si, sec in enumerate(ly.get("sections") or []):
                if not isinstance(sec, dict):
                    continue
                sections_in.append({**sec, "layout_id": lid, "sort_order": si})
    now = time.time()
    with _lock, connect() as conn:
        _migrate_schema(conn)
        conn.execute("DELETE FROM dashboard_widgets")
        conn.execute("DELETE FROM dashboard_sections")
        conn.execute("DELETE FROM dashboard_layouts")
        if flat_layouts:
            for ly in flat_layouts:
                conn.execute(
                    """
                    INSERT INTO dashboard_layouts(id, stack, sort_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (ly["id"], ly["stack"], ly["sort_order"], now, now),
                )
        else:
            default_lid = new_id()
            conn.execute(
                """
                INSERT INTO dashboard_layouts(id, stack, sort_order, created_at, updated_at)
                VALUES (?, 'horizontal', 0, ?, ?)
                """,
                (default_lid, now, now),
            )
            for sec in sections_in:
                if isinstance(sec, dict) and not sec.get("layout_id"):
                    sec["layout_id"] = default_lid
        for si, sec in enumerate(sections_in):
            if not isinstance(sec, dict):
                continue
            sid = str(sec.get("id") or new_id())
            title = str(sec.get("title") or "Section").strip() or "Section"
            collapsed = 1 if sec.get("collapsed") else 0
            stack = "horizontal"
            size = _norm_section_size(sec.get("size"))
            layout_id = str(sec.get("layout_id") or "") or None
            width_px = _norm_px(sec.get("width_px"))
            height_px = _norm_px(sec.get("height_px"))
            if width_px <= 0 and height_px <= 0:
                width_px, height_px = _SECTION_SIZE_TO_PX.get(size, (0, 0))
            sec_card_mod = _norm_card_mod(sec.get("card_mod"))
            conn.execute(
                """
                INSERT INTO dashboard_sections(
                  id, title, sort_order, collapsed, shape, size, stack,
                  layout_id, width_px, height_px, card_mod, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    title,
                    _norm_sort_order(sec.get("sort_order"), si),
                    collapsed,
                    "rectangle",
                    size,
                    stack,
                    layout_id,
                    width_px,
                    height_px,
                    sec_card_mod,
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
                w_size = _norm_widget_size(w.get("size"))
                ww = _norm_px(w.get("width_px"))
                wh = _norm_px(w.get("height_px"))
                if ww <= 0 and wh <= 0:
                    ww, wh = _WIDGET_SIZE_TO_PX.get(w_size, (120, 120))
                conn.execute(
                    """
                    INSERT INTO dashboard_widgets(
                      id, section_id, control_id, control_layout, sort_order,
                      shape, size, icon_on, icon_off, color_on, color_off,
                      width_px, height_px, control_ui, card_mod, custom_name,
                      created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        wid,
                        sid,
                        cid,
                        layout,
                        _norm_sort_order(w.get("sort_order"), wi),
                        _norm_shape(w.get("shape"), "square"),
                        w_size,
                        str(w.get("icon_on") or ""),
                        str(w.get("icon_off") or ""),
                        _norm_color(w.get("color_on")),
                        _norm_color(w.get("color_off")),
                        ww,
                        wh,
                        _norm_control_ui(w.get("control_ui")),
                        _norm_card_mod(w.get("card_mod")),
                        str(w.get("custom_name") or "").strip(),
                        now,
                        now,
                    ),
                )
    return load_dashboard()


def add_layout(stack: str = "horizontal") -> Dict[str, Any]:
    init_db()
    now = time.time()
    lid = new_id()
    with _lock, connect() as conn:
        _migrate_schema(conn)
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS m FROM dashboard_layouts"
        ).fetchone()
        order = int(row["m"]) + 1 if row else 0
        conn.execute(
            """
            INSERT INTO dashboard_layouts(id, stack, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lid, _norm_section_stack(stack), order, now, now),
        )
    return load_dashboard()


def update_layout(layout_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    now = time.time()
    sets: List[str] = []
    vals: List[Any] = []
    if "stack" in fields and fields["stack"] is not None:
        sets.append("stack = ?")
        vals.append(_norm_section_stack(fields["stack"]))
    if not sets:
        return load_dashboard()
    sets.append("updated_at = ?")
    vals.append(now)
    vals.append(layout_id)
    with _lock, connect() as conn:
        conn.execute(
            f"UPDATE dashboard_layouts SET {', '.join(sets)} WHERE id = ?",
            vals,
        )
    return load_dashboard()


def delete_layout(layout_id: str) -> Dict[str, Any]:
    init_db()
    with _lock, connect() as conn:
        secs = conn.execute(
            "SELECT id FROM dashboard_sections WHERE layout_id = ?",
            (layout_id,),
        ).fetchall()
        for s in secs:
            conn.execute(
                "DELETE FROM dashboard_widgets WHERE section_id = ?", (s["id"],)
            )
            conn.execute("DELETE FROM dashboard_sections WHERE id = ?", (s["id"],))
        conn.execute("DELETE FROM dashboard_layouts WHERE id = ?", (layout_id,))
    return load_dashboard()


def add_section(
    title: str = "New section", layout_id: Optional[str] = None
) -> Dict[str, Any]:
    init_db()
    now = time.time()
    sid = new_id()
    with _lock, connect() as conn:
        _migrate_schema(conn)
        lid = layout_id
        if not lid:
            row = conn.execute(
                """
                SELECT id FROM dashboard_layouts
                ORDER BY sort_order ASC LIMIT 1
                """
            ).fetchone()
            if row:
                lid = str(row["id"])
            else:
                lid = new_id()
                conn.execute(
                    """
                    INSERT INTO dashboard_layouts(id, stack, sort_order, created_at, updated_at)
                    VALUES (?, 'horizontal', 0, ?, ?)
                    """,
                    (lid, now, now),
                )
        row = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), -1) AS m
            FROM dashboard_sections WHERE layout_id = ?
            """,
            (lid,),
        ).fetchone()
        order = int(row["m"]) + 1 if row else 0
        conn.execute(
            """
            INSERT INTO dashboard_sections(
              id, title, sort_order, collapsed, shape, size, stack,
              layout_id, created_at, updated_at
            ) VALUES (?, ?, ?, 0, 'rectangle', 'half', 'horizontal', ?, ?, ?)
            """,
            (
                sid,
                (title or "New section").strip() or "New section",
                order,
                lid,
                now,
                now,
            ),
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
    if "layout_id" in fields and fields["layout_id"] is not None:
        sets.append("layout_id = ?")
        vals.append(str(fields["layout_id"]) or None)
    if "width_px" in fields and fields["width_px"] is not None:
        sets.append("width_px = ?")
        vals.append(_norm_px(fields["width_px"]))
    if "height_px" in fields and fields["height_px"] is not None:
        sets.append("height_px = ?")
        vals.append(_norm_px(fields["height_px"]))
    if "card_mod" in fields:
        sets.append("card_mod = ?")
        vals.append(_norm_card_mod(fields["card_mod"]))
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
    width_px: int = 0,
    height_px: int = 0,
    control_ui: str = "auto",
    card_mod: Any = None,
    custom_name: str = "",
) -> Dict[str, Any]:
    init_db()
    now = time.time()
    layout = "more" if str(control_layout).lower() in {"more", "ungrouped"} else "less"
    cid = (control_id or "").strip()
    if not cid:
        raise ValueError("control_id required")
    w_size = _norm_widget_size(size)
    ww = _norm_px(width_px)
    wh = _norm_px(height_px)
    if ww <= 0 and wh <= 0:
        ww, wh = _WIDGET_SIZE_TO_PX.get(w_size, (120, 120))
    with _lock, connect() as conn:
        _migrate_schema(conn)
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
              width_px, height_px, control_ui, card_mod, custom_name,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                section_id,
                cid,
                layout,
                order,
                _norm_shape(shape, "square"),
                w_size,
                str(icon_on or ""),
                str(icon_off or ""),
                _norm_color(color_on),
                _norm_color(color_off),
                ww,
                wh,
                _norm_control_ui(control_ui),
                _norm_card_mod(card_mod),
                str(custom_name or "").strip(),
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
    if "width_px" in fields and fields["width_px"] is not None:
        sets.append("width_px = ?")
        vals.append(_norm_px(fields["width_px"]))
    if "height_px" in fields and fields["height_px"] is not None:
        sets.append("height_px = ?")
        vals.append(_norm_px(fields["height_px"]))
    if "control_ui" in fields and fields["control_ui"] is not None:
        sets.append("control_ui = ?")
        vals.append(_norm_control_ui(fields["control_ui"]))
    if "card_mod" in fields:
        sets.append("card_mod = ?")
        vals.append(_norm_card_mod(fields["card_mod"]))
    if "custom_name" in fields and fields["custom_name"] is not None:
        sets.append("custom_name = ?")
        vals.append(str(fields["custom_name"]).strip())
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
