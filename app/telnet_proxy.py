"""Telnet proxy — multiplex external clients (PuTTY, scripts) onto the shared AVR session.

Denon allows only one telnet client to the receiver. This manager keeps that session
via DenonTelnetHub; the proxy listens on a separate port and forwards commands through
the hub so multiple local clients can share it.
"""

from __future__ import annotations

import logging
import socket
import threading
from typing import Any, Callable, Dict, List, Optional, Set

from .app_settings import load_settings
from .denon_telnet import DenonTelnetError, get_telnet_hub
from .telnet_protocol import greeting_banner, initial_negotiation, strip_telnet_protocol

log = logging.getLogger("denon.telnet_proxy")

DEFAULT_PROXY_PORT = 2323
DEFAULT_BAUD_RATE = 9600
READ_CHUNK = 4096


class TelnetProxyServer:
    def __init__(
        self,
        avr_host: str,
        listen_port: int = DEFAULT_PROXY_PORT,
        baud_rate: int = DEFAULT_BAUD_RATE,
    ) -> None:
        self.avr_host = (avr_host or "").strip()
        self.listen_port = int(listen_port)
        self.baud_rate = int(baud_rate)
        self._hub = get_telnet_hub(self.avr_host)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._listener: Optional[Callable[[List[str]], None]] = None
        self._clients_lock = threading.Lock()
        self._clients: Set[socket.socket] = set()
        self._last_error: Optional[str] = None

    def status(self) -> Dict[str, Any]:
        with self._clients_lock:
            client_count = len(self._clients)
        running = self._thread is not None and self._thread.is_alive()
        return {
            "enabled": running,
            "running": running,
            "listen_port": self.listen_port,
            "avr_host": self.avr_host,
            "baud_rate": self.baud_rate,
            "client_count": client_count,
            "last_error": self._last_error,
            "hub_connected": bool(self._hub.snapshot_cache().get("connected")),
            "putty": {
                "connection_type": "Raw or Telnet",
                "not_serial": True,
                "baud_note": (
                    f"Baud {self.baud_rate} applies to RS-232 serial adapters only; "
                    "this TCP proxy ignores baud rate."
                ),
                "command_suffix": "CR/LF (Enter in PuTTY)",
                "example": "PW?",
            },
        }

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._listener = self._fanout_events
        self._hub.add_listener(self._listener)
        self._thread = threading.Thread(
            target=self._serve_loop,
            name="telnet-proxy",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._listener is not None:
            self._hub.remove_listener(self._listener)
            self._listener = None
        with self._clients_lock:
            for sock in list(self._clients):
                try:
                    sock.close()
                except OSError:
                    pass
            self._clients.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def _fanout_events(self, lines: List[str]) -> None:
        if not lines:
            return
        payload = "".join(f"{ln}\r\n" for ln in lines if ln).encode("ascii", errors="ignore")
        if not payload:
            return
        with self._clients_lock:
            dead: List[socket.socket] = []
            for sock in self._clients:
                try:
                    sock.sendall(payload)
                except OSError:
                    dead.append(sock)
            for sock in dead:
                self._clients.discard(sock)

    def _serve_loop(self) -> None:
        srv: Optional[socket.socket] = None
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", self.listen_port))
            srv.listen(16)
            srv.settimeout(0.5)
            log.info(
                "Telnet proxy listening on 0.0.0.0:%s -> %s:23 (baud ref %s)",
                self.listen_port,
                self.avr_host,
                self.baud_rate,
            )
        except OSError as e:
            self._last_error = str(e)
            log.warning("Telnet proxy failed to bind port %s: %s", self.listen_port, e)
            return

        while not self._stop.is_set():
            try:
                client, addr = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(
                target=self._handle_client,
                args=(client, addr),
                name=f"telnet-proxy-client-{addr[0]}",
                daemon=True,
            ).start()

        if srv is not None:
            try:
                srv.close()
            except OSError:
                pass

    def _handle_client(self, sock: socket.socket, addr: Any) -> None:
        sock.settimeout(300.0)
        with self._clients_lock:
            self._clients.add(sock)
        log.info("Telnet proxy client connected: %s:%s", addr[0], addr[1])
        try:
            sock.sendall(
                greeting_banner(self.listen_port, self.avr_host, self.baud_rate)
                + initial_negotiation()
            )
        except OSError as e:
            log.warning("Telnet proxy greeting failed for %s:%s: %s", addr[0], addr[1], e)

        raw_buf = bytearray()
        line_buf = b""
        try:
            while not self._stop.is_set():
                try:
                    chunk = sock.recv(READ_CHUNK)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                raw_buf.extend(chunk)
                while raw_buf:
                    responses, payload, consumed = strip_telnet_protocol(bytes(raw_buf))
                    if consumed <= 0:
                        break
                    del raw_buf[:consumed]
                    if responses:
                        try:
                            sock.sendall(responses)
                        except OSError:
                            raise
                    if payload:
                        line_buf += payload
                    while True:
                        line, sep, rest = line_buf.partition(b"\r")
                        if not sep:
                            line, sep2, rest = line_buf.partition(b"\n")
                            if not sep2:
                                break
                        line_buf = rest
                        cmd = line.decode("ascii", errors="ignore").strip()
                        if not cmd:
                            continue
                        try:
                            result = self._hub.send(cmd)
                            out_lines = list(result.get("responses") or [])
                            if out_lines:
                                out = "".join(f"{ln}\r\n" for ln in out_lines)
                                sock.sendall(out.encode("ascii", errors="ignore"))
                        except DenonTelnetError as e:
                            sock.sendall(f"ERROR: {e}\r\n".encode("ascii", errors="ignore"))
                        except Exception as e:
                            sock.sendall(f"ERROR: {e}\r\n".encode("ascii", errors="ignore"))
        except OSError:
            pass
        finally:
            with self._clients_lock:
                self._clients.discard(sock)
            try:
                sock.close()
            except OSError:
                pass
            log.info("Telnet proxy client disconnected: %s:%s", addr[0], addr[1])


_proxy: Optional[TelnetProxyServer] = None
_proxy_lock = threading.Lock()


def restart_telnet_proxy(avr_host: str) -> Dict[str, Any]:
    global _proxy
    settings = load_settings()
    enabled = bool(settings.get("telnet_proxy_enabled"))
    port = int(settings.get("telnet_proxy_port") or DEFAULT_PROXY_PORT)
    baud = int(settings.get("telnet_proxy_baud_rate") or DEFAULT_BAUD_RATE)
    with _proxy_lock:
        if _proxy is not None:
            _proxy.stop()
            _proxy = None
        if enabled and avr_host:
            _proxy = TelnetProxyServer(avr_host, port, baud)
            _proxy.start()
        return telnet_proxy_status()


def stop_telnet_proxy() -> None:
    global _proxy
    with _proxy_lock:
        if _proxy is not None:
            _proxy.stop()
            _proxy = None


def telnet_proxy_status() -> Dict[str, Any]:
    settings = load_settings()
    port = int(settings.get("telnet_proxy_port") or DEFAULT_PROXY_PORT)
    baud = int(settings.get("telnet_proxy_baud_rate") or DEFAULT_BAUD_RATE)
    with _proxy_lock:
        if _proxy is None:
            return {
                "enabled": bool(settings.get("telnet_proxy_enabled")),
                "running": False,
                "listen_port": port,
                "baud_rate": baud,
                "client_count": 0,
                "last_error": None,
                "hub_connected": False,
                "putty": {
                    "connection_type": "Raw or Telnet",
                    "not_serial": True,
                    "baud_note": (
                        f"Baud {baud} applies to RS-232 serial adapters only; "
                        "this TCP proxy ignores baud rate."
                    ),
                    "command_suffix": "CR/LF (Enter in PuTTY)",
                    "example": "PW?",
                },
            }
        return _proxy.status()
