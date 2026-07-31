"""Denon AVR telnet client (TCP port 23).

Protocol (Ver.02): ASCII COMMAND+PARAMETER+CR, ≥50ms between commands,
~1s settle after PWON, request responses within ~200ms.
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Any, Dict, List, Optional


DEFAULT_PORT = 23
CONNECT_TIMEOUT_S = 3.0
READ_IDLE_S = 0.22
READ_CHUNK = 4096
MIN_COMMAND_GAP_S = 0.05
PWON_SETTLE_S = 1.0


class DenonTelnetError(RuntimeError):
    pass


class DenonTelnetClient:
    """Thread-safe short-lived or reused telnet session to one AVR."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = (host or "").strip()
        self.port = int(port)
        self._lock = threading.Lock()
        self._sock: Optional[socket.socket] = None
        self._last_send_at = 0.0

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _ensure_sock(self) -> socket.socket:
        if self._sock is not None:
            return self._sock
        if not self.host:
            raise DenonTelnetError("telnet host is empty")
        sock = socket.create_connection(
            (self.host, self.port), timeout=CONNECT_TIMEOUT_S
        )
        sock.settimeout(0.15)
        # Drain IAC negotiation / banner briefly.
        deadline = time.monotonic() + 0.35
        buf = bytearray()
        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(READ_CHUNK)
                if not chunk:
                    break
                buf.extend(chunk)
            except socket.timeout:
                break
            except OSError:
                break
        self._sock = sock
        return sock

    def _pace(self) -> None:
        gap = time.monotonic() - self._last_send_at
        if gap < MIN_COMMAND_GAP_S:
            time.sleep(MIN_COMMAND_GAP_S - gap)

    def _read_until_idle(self, sock: socket.socket) -> List[str]:
        buf = bytearray()
        idle_deadline = time.monotonic() + READ_IDLE_S
        while time.monotonic() < idle_deadline:
            try:
                chunk = sock.recv(READ_CHUNK)
                if not chunk:
                    break
                buf.extend(self._strip_iac(chunk))
                idle_deadline = time.monotonic() + READ_IDLE_S
            except socket.timeout:
                continue
            except OSError as e:
                raise DenonTelnetError(f"telnet read failed: {e}") from e
        text = buf.decode("ascii", errors="ignore")
        lines = [ln.strip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        return [ln for ln in lines if ln]

    @staticmethod
    def _strip_iac(data: bytes) -> bytes:
        """Remove Telnet IAC negotiation sequences."""
        out = bytearray()
        i = 0
        while i < len(data):
            b = data[i]
            if b == 255 and i + 1 < len(data):  # IAC
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

    def send(self, command: str) -> Dict[str, Any]:
        cmd = (command or "").strip()
        if not cmd:
            raise ValueError("command is empty")
        # Reject CR/LF injection
        if "\r" in cmd or "\n" in cmd:
            raise ValueError("command must not contain CR/LF")

        with self._lock:
            try:
                sock = self._ensure_sock()
                self._pace()
                payload = (cmd + "\r").encode("ascii", errors="strict")
                sock.sendall(payload)
                self._last_send_at = time.monotonic()
                if cmd.upper() == "PWON":
                    time.sleep(PWON_SETTLE_S)
                responses = self._read_until_idle(sock)
                return {
                    "request": cmd,
                    "responses": responses,
                    "transport": "telnet",
                }
            except (OSError, TimeoutError, UnicodeEncodeError) as e:
                self._close_unlocked()
                raise DenonTelnetError(str(e)) from e

    def query(self, prefix: str) -> Dict[str, Any]:
        p = (prefix or "").strip()
        if not p:
            raise ValueError("query prefix is empty")
        if p.endswith("?"):
            return self.send(p)
        # Some queries use a space before ? (e.g. PSTONE CTRL ?)
        if p.endswith(" "):
            return self.send(p + "?")
        return self.send(p if "?" in p else f"{p}?")


def host_from_base(base_url: str) -> str:
    """Extract hostname from http://host[:port]/."""
    s = (base_url or "").strip()
    if "://" in s:
        s = s.split("://", 1)[1]
    s = s.split("/", 1)[0]
    if s.startswith("[") and "]" in s:
        return s[1 : s.index("]")]
    return s.split(":", 1)[0]
