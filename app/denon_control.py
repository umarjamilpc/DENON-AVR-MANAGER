"""Unified AVR control: telnet primary, goform AppDirect fallback."""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

from .denon_client import DenonSetupClient
from .denon_telnet import DenonTelnetError, get_telnet_hub, host_from_base
from .osd_labels import channel_osd, osd_label
from .protocol_loader import (
    CONTROL_LAYOUT_GROUPED,
    CONTROL_LAYOUT_LESS,
    CONTROL_LAYOUT_MORE,
    CONTROL_LAYOUT_UNGROUPED,
    CONTROL_LAYOUTS,
    load_telnet_commands,
    load_telnet_protocol,
    normalize_layout,
)

SUPPORTED_MODELS = (
    "AVR-X1200W",
    "AVR-X2200W",
    "AVR-X3200W",
    "AVR-X4200W",
)

DIRECT = "/goform/formiPhoneAppDirect.xml"


def model_short(model: Optional[str]) -> str:
    m = (model or "AVR-X1200W").strip().upper()
    if m.startswith("AVR-"):
        m = m[4:]
    return m


def control_supported_on_model(control: Dict[str, Any], model: Optional[str]) -> bool:
    short = model_short(model)
    models = control.get("models")
    if isinstance(models, list) and models:
        return short in {str(x).upper().replace("AVR-", "") for x in models}
    # Legacy flag: curated for X1200W; treat as OK for whole X*00W family unless False
    if control.get("x1200w") is False:
        return False
    return short in {"X1200W", "X2200W", "X3200W", "X4200W"}


def filter_controls_for_model(
    controls: List[Dict[str, Any]], model: Optional[str]
) -> List[Dict[str, Any]]:
    return [c for c in controls if control_supported_on_model(c, model)]


def option_supported_on_model(opt: Dict[str, Any], model: Optional[str]) -> bool:
    models = opt.get("models")
    if not isinstance(models, list) or not models:
        return True
    short = model_short(model)
    return short in {str(x).upper().replace("AVR-", "") for x in models}


def filter_control_options(
    control: Dict[str, Any], model: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Return a control copy with model-filtered enum options, or None if empty enum."""
    cc = dict(control)
    opts = cc.get("options")
    if isinstance(opts, list) and opts:
        filtered = [o for o in opts if option_supported_on_model(o, model)]
        cc["options"] = filtered
        if cc.get("kind") == "enum" and not filtered:
            return None
    return cc


_ALWAYS_BLOCKED = frozenset(
    {
        "RM STA",
        "RMSTA",
        "RM END",
        "RMEND",
    }
)

_CONFIRM_REQUIRED_PREFIXES = (
    "SYREMOTE LOCK",
    "SYPANEL LOCK",
    "SYPANEL+V LOCK",
    "MNZST",
    "CVZRL",
    "TPANMEM",
)

# Allow request queries (COMMAND?) and typical Denon parameter chars.
_CMD_RE = re.compile(r"^[A-Z0-9 /:._+\-?]{2,40}$", re.I)


class ControlBlockedError(ValueError):
    pass


class ControlConfirmRequired(ValueError):
    pass


def _normalize_cmd(cmd: str) -> str:
    return (cmd or "").strip()


def _blocked(cmd: str, protocol: Dict[str, Any]) -> bool:
    u = cmd.upper().replace("  ", " ")
    compact = u.replace(" ", "")
    blocked = set(_ALWAYS_BLOCKED)
    for b in protocol.get("blocked_commands") or []:
        blocked.add(str(b).upper())
    for b in blocked:
        if u == b or compact == b.replace(" ", ""):
            return True
    return False


def _needs_confirm(cmd: str, protocol: Dict[str, Any]) -> bool:
    u = cmd.upper()
    if "QUICK" in u and "MEMORY" in u:
        return True
    prefixes = list(_CONFIRM_REQUIRED_PREFIXES)
    for p in protocol.get("confirm_prefixes") or []:
        prefixes.append(str(p).upper())
    # Ignore broad MSQUICK / Z2QUICK from catalog — only MEMORY is gated above
    prefixes = [p for p in prefixes if p not in {"MSQUICK", "Z2QUICK"}]
    return any(u.startswith(p) for p in prefixes)


def _build_allowlist(
    controls: List[Dict[str, Any]],
) -> Tuple[Set[str], List[Dict[str, Any]]]:
    exact: Set[str] = set()
    sliders: List[Dict[str, Any]] = []
    for c in controls:
        kind = c.get("kind")
        if kind == "raw":
            continue
        if c.get("command"):
            exact.add(str(c["command"]).upper())
        for key in ("on_command", "off_command", "up", "down"):
            if c.get(key):
                exact.add(str(c[key]).upper())
        for opt in c.get("options") or []:
            if opt.get("command"):
                exact.add(str(opt["command"]).upper())
        for key in ("up", "down"):
            if c.get(key):
                exact.add(str(c[key]).upper())
        if c.get("query"):
            exact.add(str(c["query"]).upper())
        if kind in {"slider", "stepper"} and c.get("prefix"):
            sliders.append(c)
    # Status queries from both layouts are always allowed
    for lay in CONTROL_LAYOUTS:
        proto = load_telnet_protocol(lay)
        for q in proto.get("status_queries") or []:
            exact.add(str(q).upper())
        for q in proto.get("status_queries_lite") or []:
            exact.add(str(q).upper())
    return exact, sliders


def _slider_match(cmd: str, sliders: List[Dict[str, Any]]) -> bool:
    u = cmd.upper()
    ordered = sorted(
        sliders,
        key=lambda s: len(str(s.get("prefix") or "")),
        reverse=True,
    )
    for s in ordered:
        prefix = str(s.get("prefix") or "").upper()
        if not prefix or not u.startswith(prefix):
            continue
        if s.get("space_before_value"):
            if not u.startswith(prefix + " "):
                continue
            rest = u[len(prefix) + 1 :].strip()
            if not (rest.isdigit() and len(rest) <= 3):
                continue
            val = int(rest)
        else:
            rest = u[len(prefix) :]
            if not rest.isdigit():
                continue
            pad = int(s.get("pad") or 2)
            half = bool(s.get("half_step"))
            if half and len(rest) == 3 and rest.endswith("5"):
                val = int(rest[:2])
            elif pad >= len(rest) >= 1 or (pad == 3 and len(rest) == 3):
                if len(rest) > pad and not half:
                    continue
                if len(rest) == 3 and pad == 2 and not half:
                    continue
                val = int(rest)
            else:
                continue
        lo, hi = s.get("min"), s.get("max")
        if lo is not None and val < int(lo):
            return False
        if hi is not None and val > int(hi):
            return False
        return True
    return False


def resolve_command_from_id(
    control_id: str, value: Optional[Any] = None
) -> str:
    """Map catalog control id (+ optional value) to a telnet command string."""
    cid = (control_id or "").strip()
    for c in load_telnet_commands():
        if c.get("id") != cid:
            continue
        kind = c.get("kind")
        if kind in {"action", "query"}:
            return str(c.get("command") or c.get("query") or "")
        if kind == "toggle":
            # value: true/on/1 → on_command; false/off/0 → off_command
            # or explicit command string
            if value is None:
                raise ValueError(f"control {cid} requires on/off value")
            raw = str(value).strip()
            raw_l = raw.lower()
            if raw.upper() in {
                str(c.get("on_command") or "").upper(),
                str(c.get("off_command") or "").upper(),
            }:
                return raw
            if raw_l in {"1", "true", "on", "yes"}:
                return str(c.get("on_command") or "")
            if raw_l in {"0", "false", "off", "no", "standby"}:
                return str(c.get("off_command") or "")
            raise ValueError(f"invalid toggle value for {cid}: {value!r}")
        if kind == "enum":
            if value is None:
                raise ValueError(f"control {cid} requires a value")
            want = str(value).strip()
            for opt in c.get("options") or []:
                if str(opt.get("command")) == want or str(opt.get("label")) == want:
                    return str(opt["command"])
            raise ValueError(f"invalid value for {cid}: {value!r}")
        if kind in {"slider", "stepper"}:
            # stepper with up/down as value
            if value is not None and str(value).strip().lower() in {"up", "down"}:
                key = str(value).strip().lower()
                cmd = c.get(key)
                if not cmd:
                    raise ValueError(f"{cid} has no {key} command")
                return str(cmd)
            if c.get("display_only_value") and value is None:
                raise ValueError(f"use value=up|down for {cid}")
            if value is None:
                raise ValueError(f"control {cid} requires a numeric value")
            # Sleep off
            if int(value) == 0 and c.get("off_command"):
                return str(c["off_command"])
            prefix = str(c.get("prefix") or "")
            if not prefix:
                raise ValueError(f"{cid} has no prefix for direct set")
            pad = int(c.get("pad") or 2)
            try:
                num = int(value)
            except (TypeError, ValueError) as e:
                raise ValueError(f"slider value must be int for {cid}") from e
            lo, hi = c.get("min"), c.get("max")
            if lo is not None and num < int(lo):
                raise ValueError(f"{cid} min is {lo}")
            if hi is not None and num > int(hi):
                raise ValueError(f"{cid} max is {hi}")
            body = f"{num:0{pad}d}"
            if c.get("space_before_value"):
                return f"{prefix} {body}"
            return f"{prefix}{body}"
        if kind == "raw":
            raise ValueError("use command= for raw")
    raise KeyError(f"unknown control id: {cid}")


def validate_command(
    cmd: str, *, confirm: bool = False, allow_raw: bool = False
) -> str:
    protocol = load_telnet_protocol()
    cmd = _normalize_cmd(cmd)
    if not cmd:
        raise ValueError("command is empty")
    if not _CMD_RE.match(cmd):
        raise ValueError("command contains invalid characters")
    if _blocked(cmd, protocol):
        raise ControlBlockedError(f"command blocked: {cmd}")
    if _needs_confirm(cmd, protocol) and not confirm:
        raise ControlConfirmRequired(f"command requires confirm=true: {cmd}")

    exact, sliders = _build_allowlist(load_telnet_commands())
    upper = cmd.upper()
    if upper in exact or _slider_match(cmd, sliders):
        return cmd
    if allow_raw:
        return cmd
    raise ControlBlockedError(
        f"command not in allowlist (use Advanced raw with allow_raw): {cmd}"
    )


def _mv_token_to_parts(token: str) -> Optional[Tuple[int, str, float]]:
    """Parse MV405 / MV80 → (int_for_slider, raw_token, db)."""
    t = token.upper()
    if t.startswith("MV"):
        t = t[2:]
    if not t.isdigit():
        return None
    if len(t) == 3 and t.endswith("5"):
        whole = int(t[:2])
        db = whole + 0.5 - 80
        return whole, token.upper() if token.upper().startswith("MV") else f"MV{t}", db
    whole = int(t)
    db = float(whole - 80)
    return whole, f"MV{t}", db


def _db_str_to_mv(vol: str) -> Optional[Tuple[int, str, float]]:
    s = (vol or "").strip()
    if not s or s in {"---", "MIN"}:
        return 0, "MV00", -80.0
    try:
        db = float(s)
    except ValueError:
        return None
    abs_v = 80.0 + db
    whole = int(abs_v)
    frac = abs_v - whole
    if abs(frac - 0.5) < 0.01:
        return whole, f"MV{whole}5", db
    return whole, f"MV{whole:02d}" if whole < 100 else f"MV{whole}", db


def _level_display(value: int, zero_db: Optional[int]) -> str:
    if zero_db is None:
        return str(value)
    return f"{value - int(zero_db):+d} dB ({value})"


def _match_enum_line(line: str, options: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    u = line.strip().upper()
    # Longest command match wins (MSDOLBY ATMOS vs MS)
    ranked = sorted(
        options,
        key=lambda o: len(str(o.get("command") or "")),
        reverse=True,
    )
    for opt in ranked:
        cmd = str(opt.get("command") or "").upper()
        if u == cmd or u.startswith(cmd):
            return {"command": opt.get("command"), "label": opt.get("label"), "raw": line.strip()}
    return None


def queries_for_section(
    section_id: Optional[str],
    *,
    full: bool = False,
    layout: str = CONTROL_LAYOUT_LESS,
) -> List[str]:
    layout = normalize_layout(layout)
    protocol = load_telnet_protocol(layout)
    if full and not section_id:
        return list(protocol.get("status_queries") or [])
    if not section_id:
        return list(
            protocol.get("status_queries_lite") or protocol.get("status_queries") or []
        )

    # Prefer explicit section query lists when present
    per = (protocol.get("section_queries") or {}).get(section_id)
    if per:
        return list(per)

    seen: Set[str] = set()
    out: List[str] = []
    for c in load_telnet_commands(layout):
        if c.get("section") != section_id:
            continue
        q = c.get("query")
        if q:
            qq = str(q).strip()
            key = qq.upper()
            if key not in seen:
                seen.add(key)
                out.append(qq)
    # Always include lite power/volume anchors when querying any section
    for q in ("PW?", "MV?", "MU?", "SI?"):
        if q.upper() not in seen and section_id in {
            "main",
            "power",
            "volume",
            "input",
            "surround",
        }:
            seen.add(q.upper())
            out.insert(0, q)
    return out


def parse_entities(
    responses: List[str],
    *,
    power: Optional[Dict[str, Any]] = None,
    section_id: Optional[str] = None,
    layout: str = CONTROL_LAYOUT_LESS,
) -> Dict[str, Any]:
    """Map telnet response lines (+ optional goform power) to control_id → state."""
    layout = normalize_layout(layout)
    lines = [
        ln.strip()
        for ln in responses
        if ln and str(ln).strip() and not str(ln).upper().startswith("MVMAX")
    ]
    controls = load_telnet_commands(layout)
    if section_id:
        controls = [c for c in controls if c.get("section") == section_id]

    entities: Dict[str, Any] = {}

    for c in controls:
        cid = str(c.get("id") or "")
        kind = c.get("kind")
        if not cid or kind in {"raw"}:
            continue

        if kind == "toggle":
            on_cmd = str(c.get("on_command") or "").upper()
            off_cmd = str(c.get("off_command") or "").upper()
            on_vals = {str(x).upper() for x in (c.get("on_values") or [on_cmd]) if x}
            off_vals = {str(x).upper() for x in (c.get("off_values") or [off_cmd]) if x}
            state = None
            raw_hit = None
            for ln in lines:
                u = ln.upper()
                if u in on_vals or (on_cmd and u.startswith(on_cmd)):
                    state = True
                    raw_hit = ln
                    break
                if u in off_vals or (off_cmd and (u == off_cmd or u.startswith(off_cmd))):
                    state = False
                    raw_hit = ln
                    break
                # PWSTANDBY / Z2OFF style contained in longer status lines
                if off_cmd and off_cmd in u.replace(" ", ""):
                    state = False
                    raw_hit = ln
                    break
            if state is not None:
                entities[cid] = {
                    "kind": "toggle",
                    "raw": raw_hit,
                    "value": state,
                    "on": state,
                    "command": on_cmd if state else off_cmd,
                    "display": (c.get("on_label") if state else c.get("off_label"))
                    or osd_label(raw_hit),
                }
            continue

        if kind == "enum":
            options = list(c.get("options") or [])
            hit = None
            for ln in lines:
                hit = _match_enum_line(ln, options)
                if hit:
                    break
            if hit:
                entities[cid] = {
                    "kind": "enum",
                    "raw": hit["raw"],
                    "command": hit["command"],
                    "label": hit["label"],
                    "display": osd_label(hit["command"]) or hit["label"],
                }
            continue

        if kind in {"slider", "stepper"}:
            if c.get("display_only_value"):
                q = str(c.get("query") or "").rstrip("?").upper()
                for ln in lines:
                    u = ln.upper()
                    if q and u.startswith(q):
                        entities[cid] = {
                            "kind": kind,
                            "raw": ln.strip(),
                            "display": osd_label(ln) or ln.strip(),
                        }
                        break
                continue

            prefix = str(c.get("prefix") or "").upper()
            if not prefix:
                continue
            space = bool(c.get("space_before_value"))
            half = bool(c.get("half_step"))

            # Sleep: SLPOFF / SLP030
            if prefix == "SLP":
                for ln in lines:
                    u = ln.upper().replace(" ", "")
                    if u == "SLPOFF" or u.startswith("SLPOFF"):
                        entities[cid] = {
                            "kind": kind,
                            "raw": ln.strip(),
                            "value": 0,
                            "display": "Off",
                        }
                        break
                    if u.startswith("SLP") and u[3:].isdigit():
                        mins = int(u[3:])
                        entities[cid] = {
                            "kind": kind,
                            "raw": ln.strip(),
                            "value": mins,
                            "display": f"{mins} min",
                        }
                        break
                continue

            for ln in lines:
                u = ln.upper().split()[0] if not space else ln.upper()
                if prefix == "MV":
                    if not u.startswith("MV") or u.startswith("MVMAX"):
                        continue
                    parts = _mv_token_to_parts(u)
                    if not parts:
                        continue
                    num, raw, db = parts
                    entities[cid] = {
                        "kind": kind,
                        "raw": raw,
                        "value": num,
                        "display": f"{db:g} dB",
                    }
                    break
                if space:
                    if not ln.upper().startswith(prefix + " "):
                        continue
                    rest = ln.upper()[len(prefix) + 1 :].strip().split()[0]
                    if not rest.isdigit():
                        continue
                    num = int(rest)
                    ch = prefix.replace("CV", "").replace("Z2CV", "")
                    label = channel_osd(ch) if prefix.startswith("CV") else c.get("label")
                    entities[cid] = {
                        "kind": kind,
                        "raw": ln.strip(),
                        "value": num,
                        "display": f"{label}: {_level_display(num, c.get('zero_db'))}"
                        if label
                        else _level_display(num, c.get("zero_db")),
                    }
                    break
                if not u.startswith(prefix):
                    continue
                rest = u[len(prefix) :]
                # Z2/Z3 volume is prefix + digits only (Z280), not Z2ON / Z2BD
                if prefix in {"Z2", "Z3"} and not rest.isdigit():
                    continue
                if not rest.isdigit():
                    continue
                if half and len(rest) == 3 and rest.endswith("5"):
                    num = int(rest[:2])
                else:
                    num = int(rest)
                entities[cid] = {
                    "kind": kind,
                    "raw": ln.strip(),
                    "value": num,
                    "display": _level_display(num, c.get("zero_db")),
                }
                break
            continue

        if kind in {"action", "query"}:
            cmd = str(c.get("command") or c.get("query") or "").upper().rstrip("?")
            # Highlight which discrete action matches current state (PWON vs PWSTANDBY)
            for ln in lines:
                u = ln.upper()
                if u == cmd or (cmd and u.startswith(cmd) and kind == "query"):
                    entities[cid] = {
                        "kind": kind,
                        "raw": ln,
                        "active": u == cmd or u.startswith(cmd.rstrip("?")),
                        "display": osd_label(ln),
                    }
                    break
            # Power special-case: mark active button
            if cid == "pw_on":
                for ln in lines:
                    if ln.upper() in {"PWON", "PW ON"}:
                        entities[cid] = {
                            "kind": "action",
                            "raw": ln,
                            "active": True,
                            "display": osd_label("PWON"),
                        }
            if cid == "pw_standby":
                for ln in lines:
                    if "STANDBY" in ln.upper():
                        entities[cid] = {
                            "kind": "action",
                            "raw": ln,
                            "active": True,
                            "display": osd_label("PWSTANDBY"),
                        }
            if cid == "mu_on":
                for ln in lines:
                    if ln.upper() == "MUON":
                        entities[cid] = {
                            "kind": "action",
                            "raw": ln,
                            "active": True,
                            "display": "Mute",
                        }
            if cid == "mu_off":
                for ln in lines:
                    if ln.upper() == "MUOFF":
                        entities[cid] = {
                            "kind": "action",
                            "raw": ln,
                            "active": True,
                            "display": "Unmute",
                        }

    # Channel levels: PDF — only configured speakers reply to CV?; others are inactive
    if section_id in {None, "levels", "channel"}:
        active_codes: Set[str] = set()
        for ln in lines:
            u = ln.upper()
            if not u.startswith("CV") or u.startswith("CVEND") or u.startswith("CVZRL"):
                continue
            body = u[2:]
            code = body.split()[0]
            if code.isdigit():
                continue
            active_codes.add(code)
        if active_codes:
            for c in controls:
                if c.get("section") not in {"levels", "channel"} or c.get("kind") not in {
                    "slider",
                    "stepper",
                }:
                    continue
                prefix = str(c.get("prefix") or "")
                if not prefix.upper().startswith("CV"):
                    continue
                code = prefix.upper()[2:]
                cid = str(c.get("id"))
                if code not in active_codes:
                    entities[cid] = {
                        "kind": "slider",
                        "inactive": True,
                        "display": f"{channel_osd(code)}: not in use",
                        "raw": None,
                    }

    # ZONE2 off → grey most Zone2 controls
    z2_off = any(ln.upper() in {"Z2OFF", "Z2 OFF"} for ln in lines)
    if z2_off and section_id in {None, "zone2"}:
        for c in controls:
            if c.get("section") != "zone2":
                continue
            cid = str(c.get("id"))
            if cid in {"z2_power", "z2_on"}:
                continue
            ent = entities.get(cid) or {"kind": c.get("kind")}
            ent["inactive"] = True
            if not ent.get("display"):
                ent["display"] = "ZONE2 Off"
            entities[cid] = ent

    z3_off = any(ln.upper() in {"Z3OFF", "Z3 OFF"} for ln in lines)
    if z3_off and section_id in {None, "zone3"}:
        for c in controls:
            if c.get("section") != "zone3":
                continue
            cid = str(c.get("id"))
            if cid == "z3_power":
                continue
            ent = entities.get(cid) or {"kind": c.get("kind")}
            ent["inactive"] = True
            if not ent.get("display"):
                ent["display"] = "ZONE3 Off"
            entities[cid] = ent

    # Main Zone standby → grey non-power controls
    standby = any("STANDBY" in ln.upper() for ln in lines) or (
        (power or {}).get("power") == "standby"
    )
    if standby:
        for c in controls:
            cid = str(c.get("id"))
            if cid in {"pw_power", "pw_on", "pw_standby", "pw_query"}:
                continue
            ent = entities.get(cid) or {"kind": c.get("kind")}
            ent["inactive"] = True
            if not ent.get("display"):
                ent["display"] = "Standby"
            entities[cid] = ent

    # Goform power enrichment — always sync power/mute so stale telnet cache
    # cannot leave Dashboard toggles showing Standby while the AVR is On.
    if power:
        pwr = (power.get("power") or "").lower()
        if pwr == "on":
            entities["pw_power"] = {
                **(entities.get("pw_power") or {}),
                "kind": "toggle",
                "value": True,
                "on": True,
                "raw": "PWON",
                "display": "On",
                "source": "goform",
                "inactive": False,
            }
            entities["pw_on"] = {
                **(entities.get("pw_on") or {}),
                "kind": "action",
                "raw": "PWON",
                "active": True,
                "display": "On",
                "source": "goform",
            }
            if "pw_standby" in entities:
                entities["pw_standby"]["active"] = False
        elif pwr == "standby":
            entities["pw_power"] = {
                **(entities.get("pw_power") or {}),
                "kind": "toggle",
                "value": False,
                "on": False,
                "raw": "PWSTANDBY",
                "display": "Standby",
                "source": "goform",
            }
            entities["pw_standby"] = {
                **(entities.get("pw_standby") or {}),
                "kind": "action",
                "raw": "PWSTANDBY",
                "active": True,
                "display": "Standby",
                "source": "goform",
            }
            if "pw_on" in entities:
                entities["pw_on"]["active"] = False
        if (
            "mv_master" not in entities
            and "mv_set" not in entities
            and power.get("volume") not in (None, "")
        ):
            parts = _db_str_to_mv(str(power.get("volume")))
            if parts:
                num, raw, db = parts
                vol_ent = {
                    "kind": "stepper",
                    "raw": raw,
                    "value": num,
                    "display": f"{db:g} dB",
                    "source": "goform",
                }
                entities["mv_master"] = vol_ent
                entities["mv_set"] = {**vol_ent, "kind": "slider"}
        mute = (power.get("mute") or "").lower()
        if mute in {"on", "off"}:
            entities["mu_mute"] = {
                **(entities.get("mu_mute") or {}),
                "kind": "toggle",
                "value": mute == "on",
                "on": mute == "on",
                "raw": "MUON" if mute == "on" else "MUOFF",
                "display": "Muted" if mute == "on" else "Unmuted",
                "source": "goform",
                "inactive": False,
            }
            if mute == "on":
                entities["mu_on"] = {
                    **(entities.get("mu_on") or {}),
                    "kind": "action",
                    "raw": "MUON",
                    "active": True,
                    "display": "Mute",
                    "source": "goform",
                }
                if "mu_off" in entities:
                    entities["mu_off"]["active"] = False
            else:
                entities["mu_off"] = {
                    **(entities.get("mu_off") or {}),
                    "kind": "action",
                    "raw": "MUOFF",
                    "active": True,
                    "display": "Unmute",
                    "source": "goform",
                }
                if "mu_on" in entities:
                    entities["mu_on"]["active"] = False
        inp = (power.get("input") or "").strip()
        if inp and "si_select" not in entities:
            for c in load_telnet_commands(layout):
                if c.get("id") != "si_select":
                    continue
                for opt in c.get("options") or []:
                    label = str(opt.get("label") or "")
                    if label.lower() == inp.lower() or inp.lower() in label.lower():
                        entities["si_select"] = {
                            "kind": "enum",
                            "raw": opt.get("command"),
                            "command": opt.get("command"),
                            "label": label,
                            "display": osd_label(str(opt.get("command"))) or label,
                            "source": "goform",
                        }
                        break

    return entities


class DenonControl:
    def __init__(self, http: DenonSetupClient, telnet_host: Optional[str] = None):
        self.http = http
        host = telnet_host or host_from_base(getattr(http, "base", "") or "")
        self.telnet = get_telnet_hub(host)
        self._prefer_goform = False

    def close(self) -> None:
        # Keep shared hub alive for the process (single AVR telnet slot).
        pass

    def send(
        self,
        command: str,
        *,
        confirm: bool = False,
        allow_raw: bool = False,
        force_transport: Optional[str] = None,
    ) -> Dict[str, Any]:
        cmd = validate_command(command, confirm=confirm, allow_raw=allow_raw)
        pref = (force_transport or "").strip().lower()

        if pref != "goform":
            try:
                result = self.telnet.send(cmd)
                result["ok"] = True
                return result
            except DenonTelnetError as e:
                if pref == "telnet":
                    raise
                goform = self._send_goform(cmd)
                goform["telnet_error"] = str(e)
                goform["ok"] = True
                return goform

        result = self._send_goform(cmd)
        result["ok"] = True
        return result

    def _send_goform(self, cmd: str) -> Dict[str, Any]:
        path = f"{DIRECT}?{quote(cmd, safe='/: ')}"
        body = self.http.get(path)
        if cmd.upper() in {"PWON", "PWSTANDBY", "ZMON", "ZMOFF", "Z2ON", "Z2OFF"}:
            time.sleep(0.5)
        return {
            "request": cmd,
            "responses": [],
            "transport": "goform",
            "goform_body": (body or "")[:500],
        }

    def query(
        self,
        prefix: str,
        *,
        force_transport: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = (prefix or "").strip()
        if not p:
            raise ValueError("query prefix is empty")
        if "?" in p:
            cmd = p
        elif p.endswith(" "):
            cmd = p + "?"
        else:
            cmd = p + "?"
        return self.send(cmd, allow_raw=True, force_transport=force_transport)

    def status_snapshot(
        self,
        *,
        full: bool = False,
        section: Optional[str] = None,
        max_queries: Optional[int] = None,
        power: Optional[Dict[str, Any]] = None,
        refresh: bool = True,
        model: Optional[str] = None,
        layout: str = CONTROL_LAYOUT_LESS,
    ) -> Dict[str, Any]:
        layout = normalize_layout(layout)
        if not refresh:
            lines = self.telnet.cached_lines()
            entities = parse_entities(
                lines, power=power, section_id=section, layout=layout
            )
            if model:
                allowed = {
                    str(c.get("id"))
                    for c in filter_controls_for_model(
                        load_telnet_commands(layout), model
                    )
                }
                entities = {k: v for k, v in entities.items() if k in allowed}
            cache = self.telnet.snapshot_cache()
            return {
                "ok": True,
                "section": section,
                "layout": layout,
                "transport": "cache",
                "from_cache": True,
                "responses": lines,
                "by_query": {},
                "entities": entities,
                "errors": [],
                "queried": [],
                "telnet": {
                    "connected": cache.get("connected"),
                    "last_error": cache.get("last_error"),
                },
            }

        queries = queries_for_section(section, full=full, layout=layout)
        if max_queries is not None:
            queries = queries[: max(0, int(max_queries))]

        lines: List[str] = []
        by_query: Dict[str, List[str]] = {}
        transport_used: Optional[str] = None
        errors: List[str] = []

        for q in queries:
            cmd = str(q).strip()
            try:
                result = self.send(cmd, allow_raw=True, force_transport="telnet")
            except DenonTelnetError as e:
                try:
                    result = self.send(cmd, allow_raw=True, force_transport="goform")
                    result["telnet_error"] = str(e)
                except Exception as e2:
                    errors.append(f"{cmd}: {e2}")
                    continue
            except Exception as e:
                errors.append(f"{cmd}: {e}")
                continue
            transport_used = result.get("transport") or transport_used
            resp = list(result.get("responses") or [])
            lines.extend(resp)
            by_query[cmd] = resp

        # Merge any cached event lines
        for ln in self.telnet.cached_lines():
            if ln not in lines:
                lines.append(ln)

        entities = parse_entities(
            lines, power=power, section_id=section, layout=layout
        )
        if model:
            allowed = {
                str(c.get("id"))
                for c in filter_controls_for_model(load_telnet_commands(layout), model)
            }
            entities = {k: v for k, v in entities.items() if k in allowed}

        try:
            from .mqtt_service import notify_entities

            notify_entities(entities)
        except Exception:
            pass

        cache = self.telnet.snapshot_cache()
        return {
            "ok": True,
            "section": section,
            "layout": layout,
            "transport": transport_used or "unknown",
            "from_cache": False,
            "responses": lines,
            "by_query": by_query,
            "entities": entities,
            "errors": errors,
            "queried": queries,
            "telnet": {
                "connected": cache.get("connected"),
                "last_error": cache.get("last_error"),
            },
        }

    def catalog(
        self,
        model: Optional[str] = None,
        *,
        show_zone2: bool = False,
        show_zone3: bool = False,
        layout: str = CONTROL_LAYOUT_LESS,
    ) -> Dict[str, Any]:
        layout = normalize_layout(layout)
        protocol = load_telnet_protocol(layout)
        model_name = model or "AVR-X1200W"
        raw_controls = filter_controls_for_model(
            list(protocol.get("controls") or []), model_name
        )
        controls: List[Dict[str, Any]] = []
        for c in raw_controls:
            sec = c.get("section")
            # Zone opt-in only in less-controls mode (more always shows all)
            if layout == CONTROL_LAYOUT_LESS:
                if sec == "zone2" and not show_zone2:
                    continue
                if sec == "zone3" and not show_zone3:
                    continue
            filtered = filter_control_options(c, model_name)
            if filtered is not None:
                controls.append(filtered)
        section_ids = {c.get("section") for c in controls}
        sections = [
            s
            for s in (protocol.get("sections") or [])
            if s.get("id") in section_ids
        ]
        return {
            "model": model_name,
            "models": list(SUPPORTED_MODELS),
            "layout": layout,
            "layouts": list(CONTROL_LAYOUTS),
            "protocol_version": protocol.get("protocol_version"),
            "sections": sections,
            "controls": controls,
            "show_zone2": bool(show_zone2),
            "show_zone3": bool(show_zone3),
            "telnet_note": (
                "Denon allows only one telnet (TCP 23) client. This manager keeps a "
                "single shared session — close other telnet apps while it is running."
            ),
        }

    def preload_all_status(
        self, *, model: Optional[str] = None, power: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query full status_queries once into the shared telnet cache (startup)."""
        return self.status_snapshot(
            full=True,
            section=None,
            power=power,
            refresh=True,
            model=model,
            layout=CONTROL_LAYOUT_MORE,
        )
