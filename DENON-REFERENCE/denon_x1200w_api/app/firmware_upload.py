"""Local firmware file upload to Denon bootloader formPostHandler.

Denon UI (bl_firmware_update.asp):
  POST /goform/formPostHandler  multipart/form-data
  - appFirmware: file
  - appFirmwareFile: Upload

Normal SETUP Web Update first transitions the AVR into this mode.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional, Tuple

from .denon_client import DenonSetupClient
from .field_labels import clean_display_text
from .firmware_actions import run_firmware_action

UPLOAD_HANDLER = "/goform/formPostHandler"
BOOTLOADER_INDEX = "/bl_index.asp"
BOOTLOADER_UPDATE = "/1000/bl_firmware_update.asp"

# Soft limit — real Denon packages are usually under this
MAX_FIRMWARE_BYTES = 80 * 1024 * 1024


def _page_reachable(
    client: DenonSetupClient, path: str, *, timeout: float = 5.0
) -> Tuple[bool, str]:
    old = client.timeout
    client.timeout = timeout
    try:
        html = client.get(path)
        return True, html
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        client.timeout = old


def local_upload_status(client: DenonSetupClient) -> Dict[str, Any]:
    """Whether the AVR is in bootloader upload UI."""
    # Short probes — bootloader pages hang/404 when in normal SETUP.
    bl_ok, bl_html_or_err = _page_reachable(client, BOOTLOADER_UPDATE, timeout=4.0)
    idx_ok, _ = _page_reachable(client, BOOTLOADER_INDEX, timeout=3.0)
    setup_ok, _ = _page_reachable(
        client, "/SETUP/GENERAL/FIRMWARE/d_firmware.asp", timeout=8.0
    )
    airplay = ""
    if bl_ok and isinstance(bl_html_or_err, str):
        m = re.search(
            r"AirPlay\s+firmware\s+version\s*:?\s*([^\s<]+)",
            bl_html_or_err,
            re.I,
        )
        if m:
            airplay = m.group(1).strip()
    return {
        "bootloader_upload_ready": bl_ok,
        "bootloader_index_active": idx_ok,
        "normal_firmware_setup_available": setup_ok,
        "upload_handler": UPLOAD_HANDLER,
        "airplay_firmware_version": airplay,
        "max_bytes": MAX_FIRMWARE_BYTES,
        "note": (
            "Local upload posts multipart to formPostHandler (same as Denon "
            "bl_firmware_update.asp). AVR must be in update/bootloader UI, "
            "or the API can enter Web Update mode first."
        ),
        "bootloader_detail": None if bl_ok else bl_html_or_err[:240],
    }


def _validate_firmware_bytes(filename: str, data: bytes) -> None:
    if not data:
        raise ValueError("Empty firmware file")
    if len(data) > MAX_FIRMWARE_BYTES:
        raise ValueError(
            f"Firmware file too large ({len(data)} bytes). "
            f"Max allowed is {MAX_FIRMWARE_BYTES} bytes."
        )
    name = (filename or "").strip()
    if not name:
        raise ValueError("Missing filename")
    # Soft extension hint only — Denon packages vary (.bin / .zip / no ext)
    lower = name.lower()
    if lower.endswith((".exe", ".js", ".html", ".htm", ".php")):
        raise ValueError(f"Refusing suspicious firmware filename: {name}")


def enter_bootloader_via_web_update(
    client: DenonSetupClient, *, wait_seconds: float = 25.0
) -> Dict[str, Any]:
    """Trigger Web Update then wait for bl_firmware_update.asp."""
    action = run_firmware_action(client, "web_update", timeout=30.0)
    deadline = time.time() + wait_seconds
    last_err = ""
    while time.time() < deadline:
        ok, html_or_err = _page_reachable(client, BOOTLOADER_UPDATE)
        if ok:
            return {
                "entered": True,
                "web_update": action,
                "waited_seconds": round(wait_seconds - (deadline - time.time()), 1),
            }
        last_err = str(html_or_err)
        time.sleep(1.5)
    return {
        "entered": False,
        "web_update": action,
        "error": last_err or "Bootloader upload page did not become available",
    }


def upload_local_firmware(
    client: DenonSetupClient,
    *,
    filename: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    enter_bootloader_if_needed: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Upload a local firmware package to the AVR (or validate only if dry_run)."""
    _validate_firmware_bytes(filename, data)
    status = local_upload_status(client)
    steps: Dict[str, Any] = {"status_before": status}

    if dry_run:
        return {
            "dry_run": True,
            "uploaded": False,
            "filename": filename,
            "bytes": len(data),
            "would_post_to": UPLOAD_HANDLER,
            "bootloader_upload_ready": status["bootloader_upload_ready"],
            "note": "Validated only — nothing was sent to the AVR.",
            **steps,
        }

    if not status["bootloader_upload_ready"] and enter_bootloader_if_needed:
        steps["enter_bootloader"] = enter_bootloader_via_web_update(client)
        status = local_upload_status(client)
        steps["status_after_enter"] = status

    if not status["bootloader_upload_ready"]:
        raise RuntimeError(
            "AVR is not in local firmware upload mode "
            f"({BOOTLOADER_UPDATE} unreachable). "
            "Open Web Update on the AVR first, or retry with enter_bootloader_if_needed."
        )

    # Field names match Denon bl_firmware_update.asp
    response = client.post_multipart(
        UPLOAD_HANDLER,
        fields={"appFirmwareFile": "Upload"},
        files={
            "appFirmware": (
                filename,
                data,
                content_type or "application/octet-stream",
            )
        },
    )
    snippet = clean_display_text(
        re.sub(r"<script[\s\S]*?</script>", " ", response or "", flags=re.I)
    )
    snippet = re.sub(r"\s+", " ", snippet).strip()[:400]

    return {
        "dry_run": False,
        "uploaded": True,
        "filename": filename,
        "bytes": len(data),
        "post_path": UPLOAD_HANDLER,
        "response_snippet": snippet,
        "note": (
            "Upload posted. Do not power off the AVR. Watch the front display / "
            "bl_index.asp until it finishes and returns to normal SETUP."
        ),
        **steps,
        "status_after": local_upload_status(client),
    }
