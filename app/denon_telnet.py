"""Denon AVR telnet hub — one TCP:23 session (AVR allows only a single client).

Keeps a persistent connection, caches EVENT/RESPONSE lines for instant UI reads,
and serializes all sends so Setup polling / Control Panel never open parallel sockets.
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


DEFAULT_PORT = 23
CONNECT_TIMEOUT_S = 3.0
READ_IDLE_S = 0.20
READ_CHUNK = 4096
MIN_COMMAND_GAP_S = 0.05
PWON_SETTLE_S = 1.0
EVENT_DRAIN_S = 0.05


class DenonTelnetError(RuntimeError):
    pass


def host_from_base(base_url: str) -> str:
    s = (base_url or "").strip()
    if "://" in s:
        s = s.split("://", 1)[1]
    s = s.split("/", 1)[0]
    if s.startswith("[") and "]" in s:
        return s[1 : s.index("]")]
    return s.split(":", 1)[0]


def _strip_iac(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b == 255 and i + 1 < len(data):
            cmd = data[i + 1]
            if cmd in (251, 252, 253, 254) and i + 2 < len(data):
                i += 3
                continue
            if cmd == 255:
                out.append(255)
                i += 2
                continue
            i += 2
            continue
        out.append(b)
        i += 1
    return bytes(out)


def _lines_from_buf(buf: bytes) -> List[str]:
    text = buf.decode("ascii", errors="ignore")
    parts = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return [ln.strip() for ln in parts if ln.strip()]


class DenonTelnetHub:
    """Process-wide single telnet session + line cache."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = (host or "").strip()
        self.port = int(port)
        self._lock = threading.RLock()
        self._sock: Optional[socket.socket] = None
        self._last_send_at = 0.0
        self._cache: Dict[str, str] = {}  # key → latest raw line
        self._recent: List[str] = []
        self._connected_at: Optional[float] = None
        self._last_error: Optional[str] = None
        self._reader_stop = threading.Event()
        self._reader: Optional[threading.Thread] = None
        self._listeners: List[Callable[[List[str]], None]] = []

    def add_listener(self, cb: Callable[[List[str]], None]) -> None:
        with self._lock:
            if cb not in self._listeners:
                self._listeners.append(cb)

    def remove_listener(self, cb: Callable[[List[str]], None]) -> None:
        with self._lock:
            if cb in self._listeners:
                self._listeners.remove(cb)

    def _notify_listeners(self, lines: List[str]) -> None:
        for cb in list(self._listeners):
            try:
                cb(lines)
            except Exception:
                pass

    # ---- cache helpers ----

    def snapshot_cache(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "lines": dict(self._cache),
                "recent": list(self._recent[-80:]),
                "connected": self._sock is not None,
                "host": self.host,
                "last_error": self._last_error,
            }

    def cached_lines(self) -> List[str]:
        with self._lock:
            return list(self._cache.values())

    def _ingest(self, lines: List[str], *, notify: bool = False) -> None:
        for ln in lines:
            if not ln:
                continue
            self._recent.append(ln)
            if len(self._recent) > 200:
                self._recent = self._recent[-200:]
            key = self._cache_key(ln)
            if key:
                self._cache[key] = ln
        if notify and lines:
            self._notify_listeners(lines)

    @staticmethod
    def _cache_key(line: str) -> Optional[str]:
        u = line.upper()
        if u.startswith("MVMAX"):
            return "MVMAX"
        # Multi-token PS / VS / SY style: keep first token group
        for prefix in (
            "CVFL",
            "CVFR",
            "CVC",
            "CVSW2",
            "CVSW",
            "CVSL",
            "CVSR",
            "CVSBL",
            "CVSBR",
            "CVSB",
            "CVFHL",
            "CVFHR",
            "CVTFL",
            "CVTFR",
            "CVTML",
            "CVTMR",
            "CVFDL",
            "CVFDR",
            "CVSDL",
            "CVSDR",
            "Z2CVFL",
            "Z2CVFR",
            "Z2MU",
            "Z2SLP",
            "Z2STBY",
            "PSMULTEQ",
            "PSDYNEQ",
            "PSREFLEV",
            "PSDYNVOL",
            "PSCINEMA",
            "PSTONE",
            "PSBAS",
            "PSTRE",
            "PSDIL",
            "PSSWL",
            "PSLOM",
            "PSDRC",
            "PSDIC",
            "PSLFE",
            "PSEFF",
            "PSDEL",
            "PSGEQ",
            "PSHEQ",
            "PSDSX",
            "VSASP",
            "VSSC",
            "VSSCH",
            "VSAUDIO",
            "VSVPM",
            "MSQUICK",
            "MNMEN",
            "MNZST",
            "TFAN",
            "TPAN",
            "TMAN",
            "DIM",
        ):
            if u.startswith(prefix):
                return prefix
        if u.startswith("MV"):
            return "MV"
        if u.startswith("MU"):
            return "MU"
        if u.startswith("PW"):
            return "PW"
        if u.startswith("ZM"):
            return "ZM"
        if u.startswith("SI"):
            return "SI"
        if u.startswith("SD"):
            return "SD"
        if u.startswith("DC"):
            return "DC"
        if u.startswith("SV"):
            return "SV"
        if u.startswith("MS"):
            return "MS"
        if u.startswith("SLP"):
            return "SLP"
        if u.startswith("STBY"):
            return "STBY"
        if u.startswith("ECO"):
            return "ECO"
        if u.startswith("Z2") and len(u) > 2 and u[2:].split()[0].isdigit():
            return "Z2VOL"
        if u.startswith("Z2"):
            return "Z2"
        return u.split()[0][:12]

    # ---- connection ----

    def close(self) -> None:
        self._reader_stop.set()
        with self._lock:
            self._close_unlocked()
        if self._reader and self._reader.is_alive():
            self._reader.join(timeout=1.0)
        self._reader = None

    def _close_unlocked(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
            self._connected_at = None

    def _ensure_sock(self) -> socket.socket:
        if self._sock is not None:
            return self._sock
        if not self.host:
            raise DenonTelnetError("telnet host is empty")
        try:
            sock = socket.create_connection(
                (self.host, self.port), timeout=CONNECT_TIMEOUT_S
            )
        except OSError as e:
            self._last_error = str(e)
            raise DenonTelnetError(
                f"telnet connect failed ({self.host}:{self.port}): {e}. "
                "Denon allows only one telnet client — close other apps using port 23."
            ) from e
        sock.settimeout(0.15)
        deadline = time.monotonic() + 0.35
        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(READ_CHUNK)
                if not chunk:
                    break
                self._ingest(_lines_from_buf(_strip_iac(chunk)))
            except socket.timeout:
                break
            except OSError:
                break
        self._sock = sock
        self._connected_at = time.monotonic()
        self._last_error = None
        self._start_reader()
        return sock

    def _start_reader(self) -> None:
        if self._reader and self._reader.is_alive():
            return
        self._reader_stop.clear()
        self._reader = threading.Thread(
            target=self._reader_loop, name="denon-telnet-events", daemon=True
        )
        self._reader.start()

    def _reader_loop(self) -> None:
        """Ingest unsolicited EVENTs while idle (remote / OSD changes)."""
        while not self._reader_stop.is_set():
            time.sleep(EVENT_DRAIN_S)
            if not self._lock.acquire(blocking=False):
                continue
            try:
                sock = self._sock
                if sock is None:
                    continue
                try:
                    sock.settimeout(0.08)
                    chunk = sock.recv(READ_CHUNK)
                    if not chunk:
                        self._close_unlocked()
                        self._last_error = "telnet disconnected"
                        continue
                    ingested = _lines_from_buf(_strip_iac(chunk))
                    self._ingest(ingested, notify=True)
                except socket.timeout:
                    pass
                except OSError as e:
                    self._last_error = str(e)
                    self._close_unlocked()
            finally:
                self._lock.release()

    def _pace(self) -> None:
        gap = time.monotonic() - self._last_send_at
        if gap < MIN_COMMAND_GAP_S:
            time.sleep(MIN_COMMAND_GAP_S - gap)

    def _read_until_idle(self, sock: socket.socket) -> List[str]:
        buf = bytearray()
        idle_deadline = time.monotonic() + READ_IDLE_S
        while time.monotonic() < idle_deadline:
            try:
                sock.settimeout(0.12)
                chunk = sock.recv(READ_CHUNK)
                if not chunk:
                    break
                buf.extend(_strip_iac(chunk))
                idle_deadline = time.monotonic() + READ_IDLE_S
            except socket.timeout:
                continue
            except OSError as e:
                raise DenonTelnetError(f"telnet read failed: {e}") from e
        return _lines_from_buf(bytes(buf))

    def send(self, command: str) -> Dict[str, Any]:
        cmd = (command or "").strip()
        if not cmd:
            raise ValueError("command is empty")
        if "\r" in cmd or "\n" in cmd:
            raise ValueError("command must not contain CR/LF")

        with self._lock:
            try:
                sock = self._ensure_sock()
                self._pace()
                sock.sendall((cmd + "\r").encode("ascii", errors="strict"))
                self._last_send_at = time.monotonic()
                if cmd.upper() == "PWON":
                    time.sleep(PWON_SETTLE_S)
                responses = self._read_until_idle(sock)
                self._ingest(responses)
                return {
                    "request": cmd,
                    "responses": responses,
                    "transport": "telnet",
                    "session": "shared",
                }
            except (OSError, TimeoutError, UnicodeEncodeError) as e:
                self._last_error = str(e)
                self._close_unlocked()
                raise DenonTelnetError(str(e)) from e

    def query(self, prefix: str) -> Dict[str, Any]:
        p = (prefix or "").strip()
        if not p:
            raise ValueError("query prefix is empty")
        if "?" in p:
            return self.send(p)
        if p.endswith(" "):
            return self.send(p + "?")
        return self.send(f"{p}?")


# Process singleton keyed by host
_HUBS: Dict[str, DenonTelnetHub] = {}
_HUBS_LOCK = threading.Lock()


def get_telnet_hub(host: str, port: int = DEFAULT_PORT) -> DenonTelnetHub:
    key = f"{(host or '').strip()}:{int(port)}"
    with _HUBS_LOCK:
        hub = _HUBS.get(key)
        if hub is None or hub.host != (host or "").strip():
            if hub is not None:
                hub.close()
            hub = DenonTelnetHub(host, port)
            _HUBS[key] = hub
        return hub


# Back-compat alias used by older imports
class DenonTelnetClient(DenonTelnetHub):
    """Alias — prefer get_telnet_hub() for the shared session."""

    pass
