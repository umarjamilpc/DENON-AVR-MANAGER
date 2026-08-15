"""Minimal Telnet (RFC 854) helpers for PuTTY / telnet clients on the TCP proxy."""

from __future__ import annotations

IAC = 255
DONT = 254
DO = 253
WILL = 251
WONT = 252
SB = 250
SE = 240

# Telnet option codes
ECHO = 1
SGA = 3

# Only negotiate Suppress Go Ahead — never offer ECHO (PuTTY hides local typing otherwise).
_ACCEPT_DO = {SGA}


def greeting_banner(
    listen_port: int,
    avr_host: str,
    baud_rate: int = 9600,
) -> bytes:
    target = avr_host if ":" in avr_host else f"{avr_host}:23"
    text = (
        f"\r\nDenon AVR Manager — telnet proxy (TCP {listen_port} -> {target})\r\n"
        "Send Denon telnet commands ending with CR/LF (e.g. PW? then Enter).\r\n"
        "PuTTY: Connection type = Raw or Telnet (not Serial).\r\n"
        f"Baud {baud_rate} is for RS-232 serial only; ignored on this TCP proxy.\r\n\r\n"
    )
    return text.encode("ascii", errors="replace")


def initial_negotiation() -> bytes:
    """Offer SGA only — do not offer ECHO or PuTTY suppresses local typing."""
    return bytes([IAC, WILL, SGA])


def strip_telnet_protocol(data: bytes) -> tuple[bytes, bytes, int]:
    """Split incoming bytes into (telnet_responses, user_payload, bytes_consumed)."""
    responses = bytearray()
    payload = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b != IAC:
            payload.append(b)
            i += 1
            continue
        if i + 1 >= n:
            break
        cmd = data[i + 1]
        if cmd == IAC:
            payload.append(IAC)
            i += 2
            continue
        if cmd in (DO, DONT, WILL, WONT):
            if i + 2 >= n:
                break
            opt = data[i + 2]
            if cmd == DO:
                if opt in _ACCEPT_DO:
                    responses.extend([IAC, WILL, opt])
                else:
                    responses.extend([IAC, WONT, opt])
            elif cmd == DONT:
                responses.extend([IAC, WONT, opt])
            elif cmd == WILL:
                if opt == SGA:
                    responses.extend([IAC, DO, opt])
                else:
                    # Never accept remote ECHO — PuTTY should use local echo.
                    responses.extend([IAC, DONT, opt])
            elif cmd == WONT:
                responses.extend([IAC, DONT, opt])
            i += 3
            continue
        if cmd == SB:
            j = i + 2
            while j < n - 1:
                if data[j] == IAC and data[j + 1] == SE:
                    j += 2
                    break
                j += 1
            i = j
            continue
        i += 2
    return bytes(responses), bytes(payload), i
