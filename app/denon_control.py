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

_CMD_RE = re.compile(r"^[A-Z0-9 /:._+\-]{2,40}$", re.I)


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

        try_telnet = pref == "telnet" or (
            pref != "goform" and not self._prefer_goform
        )

        if try_telnet:
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
                self._prefer_goform = True
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
        max_queries: Optional[int] = None,
    ) -> Dict[str, Any]:
        protocol = load_telnet_protocol()
        if full:
            queries = list(protocol.get("status_queries") or [])
        else:
            queries = list(
                protocol.get("status_queries_lite")
                or protocol.get("status_queries")
                or []
            )
        if max_queries is not None:
            queries = queries[: max(0, int(max_queries))]

        lines: List[str] = []
        by_query: Dict[str, List[str]] = {}
        transport_used: Optional[str] = None
        errors: List[str] = []

        for q in queries:
            cmd = str(q).strip()
            try:
                result = self.send(cmd, allow_raw=True)
            except Exception as e:
                errors.append(f"{cmd}: {e}")
                continue
            transport_used = result.get("transport") or transport_used
            resp = list(result.get("responses") or [])
            lines.extend(resp)
            by_query[cmd] = resp

        return {
            "ok": True,
            "transport": transport_used
            or ("goform" if self._prefer_goform else "unknown"),
            "responses": lines,
            "by_query": by_query,
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
