"""Unified AVR control: telnet primary, goform AppDirect fallback."""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

from .denon_client import DenonSetupClient
from .denon_telnet import DenonTelnetClient, DenonTelnetError, host_from_base
from .protocol_loader import load_telnet_commands, load_telnet_protocol

DIRECT = "/goform/formiPhoneAppDirect.xml"

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
        for opt in c.get("options") or []:
            if opt.get("command"):
                exact.add(str(opt["command"]).upper())
        for key in ("up", "down"):
            if c.get(key):
                exact.add(str(c[key]).upper())
        if c.get("query"):
            exact.add(str(c["query"]).upper())
        if kind == "slider" and c.get("prefix"):
            sliders.append(c)
    # Status queries from protocol are always allowed
    proto = load_telnet_protocol()
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
        if kind == "enum":
            if value is None:
                raise ValueError(f"control {cid} requires a value")
            want = str(value).strip()
            for opt in c.get("options") or []:
                if str(opt.get("command")) == want or str(opt.get("label")) == want:
                    return str(opt["command"])
            raise ValueError(f"invalid value for {cid}: {value!r}")
        if kind == "slider":
            if value is None:
                raise ValueError(f"control {cid} requires a numeric value")
            prefix = str(c.get("prefix") or "")
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


def queries_for_section(section_id: Optional[str], *, full: bool = False) -> List[str]:
    protocol = load_telnet_protocol()
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
    for c in load_telnet_commands():
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
) -> Dict[str, Any]:
    """Map telnet response lines (+ optional goform power) to control_id → state."""
    lines = [
        ln.strip()
        for ln in responses
        if ln and str(ln).strip() and not str(ln).upper().startswith("MVMAX")
    ]
    controls = load_telnet_commands()
    if section_id:
        controls = [c for c in controls if c.get("section") == section_id]

    entities: Dict[str, Any] = {}

    for c in controls:
        cid = str(c.get("id") or "")
        kind = c.get("kind")
        if not cid or kind in {"raw"}:
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
                    "display": hit["label"],
                }
            continue

        if kind == "slider":
            prefix = str(c.get("prefix") or "").upper()
            space = bool(c.get("space_before_value"))
            half = bool(c.get("half_step"))
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
                        "kind": "slider",
                        "raw": raw,
                        "value": num,
                        "display": f"{db:g} dB ({raw})",
                    }
                    break
                if space:
                    if not ln.upper().startswith(prefix + " "):
                        continue
                    rest = ln.upper()[len(prefix) + 1 :].strip().split()[0]
                    if not rest.isdigit():
                        continue
                    num = int(rest)
                    entities[cid] = {
                        "kind": "slider",
                        "raw": ln.strip(),
                        "value": num,
                        "display": _level_display(num, c.get("zero_db")),
                    }
                    break
                if not u.startswith(prefix):
                    continue
                rest = u[len(prefix) :]
                if not rest.isdigit():
                    continue
                # Z2 volume is Z2 + digits only (Z280), not Z2ON / Z2BD
                if prefix == "Z2" and not rest.isdigit():
                    continue
                if half and len(rest) == 3 and rest.endswith("5"):
                    num = int(rest[:2])
                else:
                    num = int(rest)
                entities[cid] = {
                    "kind": "slider",
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
                        "display": ln,
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
                            "display": "On",
                        }
            if cid == "pw_standby":
                for ln in lines:
                    if "STANDBY" in ln.upper():
                        entities[cid] = {
                            "kind": "action",
                            "raw": ln,
                            "active": True,
                            "display": "Standby",
                        }
            if cid == "mu_on":
                for ln in lines:
                    if ln.upper() == "MUON":
                        entities[cid] = {
                            "kind": "action",
                            "raw": ln,
                            "active": True,
                            "display": "Muted",
                        }
            if cid == "mu_off":
                for ln in lines:
                    if ln.upper() == "MUOFF":
                        entities[cid] = {
                            "kind": "action",
                            "raw": ln,
                            "active": True,
                            "display": "Unmuted",
                        }

    # Goform power enrichment / override gaps
    if power:
        pwr = (power.get("power") or "").lower()
        if "pw_on" not in entities and pwr == "on":
            entities["pw_on"] = {
                "kind": "action",
                "raw": "PWON",
                "active": True,
                "display": "On",
                "source": "goform",
            }
        if "pw_standby" not in entities and pwr == "standby":
            entities["pw_standby"] = {
                "kind": "action",
                "raw": "PWSTANDBY",
                "active": True,
                "display": "Standby",
                "source": "goform",
            }
        if "mv_set" not in entities and power.get("volume") not in (None, ""):
            parts = _db_str_to_mv(str(power.get("volume")))
            if parts:
                num, raw, db = parts
                entities["mv_set"] = {
                    "kind": "slider",
                    "raw": raw,
                    "value": num,
                    "display": f"{db:g} dB ({raw})",
                    "source": "goform",
                }
        mute = (power.get("mute") or "").lower()
        if mute in {"on", "off"}:
            if mute == "on":
                entities["mu_on"] = {
                    "kind": "action",
                    "raw": "MUON",
                    "active": True,
                    "display": "Muted",
                    "source": "goform",
                }
            else:
                entities["mu_off"] = {
                    "kind": "action",
                    "raw": "MUOFF",
                    "active": True,
                    "display": "Unmuted",
                    "source": "goform",
                }
        inp = (power.get("input") or "").strip()
        if inp and "si_select" not in entities:
            # Fuzzy match friendly name to SI options
            for c in load_telnet_commands():
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
                            "display": label,
                            "source": "goform",
                        }
                        break

    return entities


class DenonControl:
    def __init__(self, http: DenonSetupClient, telnet_host: Optional[str] = None):
        self.http = http
        host = telnet_host or host_from_base(getattr(http, "base", "") or "")
        self.telnet = DenonTelnetClient(host)
        self._prefer_goform = False

    def close(self) -> None:
        self.telnet.close()

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

        # Always try telnet first unless explicitly forced to goform.
        # Do not permanently stick to goform after one failure (status needs telnet).
        if pref != "goform":
            try:
                result = self.telnet.send(cmd)
                result["ok"] = True
                self._prefer_goform = False
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
    ) -> Dict[str, Any]:
        queries = queries_for_section(section, full=full)
        if max_queries is not None:
            queries = queries[: max(0, int(max_queries))]

        lines: List[str] = []
        by_query: Dict[str, List[str]] = {}
        transport_used: Optional[str] = None
        errors: List[str] = []

        for q in queries:
            cmd = str(q).strip()
            try:
                # Prefer telnet for status so we get response lines
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

        entities = parse_entities(lines, power=power, section_id=section)

        return {
            "ok": True,
            "section": section,
            "transport": transport_used or "unknown",
            "responses": lines,
            "by_query": by_query,
            "entities": entities,
            "errors": errors,
            "queried": queries,
        }

    def catalog(self) -> Dict[str, Any]:
        protocol = load_telnet_protocol()
        return {
            "model": protocol.get("model"),
            "protocol_version": protocol.get("protocol_version"),
            "sections": protocol.get("sections") or [],
            "controls": protocol.get("controls") or [],
        }
