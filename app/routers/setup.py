from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from ..denon_client import DenonSetupClient
from ..denon_power import (
    STANDBY_SETTINGS_BLOCKED,
    main_zone_is_standby,
    read_main_zone_power,
    set_main_zone_power,
    toggle_main_zone_power,
)
from ..denon_menu_status import (
    SETUP_LOCK_ENDPOINT_ID,
    SETUP_LOCK_REASON,
    apply_setup_lock_to_menu,
    is_setup_locked,
    page_has_editable_controls,
    scrape_live_menu_availability,
)
from ..firmware_actions import FIRMWARE_ACTIONS, run_firmware_action
from ..firmware_upload import local_upload_status, upload_local_firmware
from ..field_labels import attach_field_labels
from ..field_layout import layout_fields, menu_inactive_flags
from ..information_page import build_information_editor_fields
from ..host_utils import rewrite_url, scrub_host_urls
from ..info import fetch_info_dashboard
from ..protocol_loader import get_endpoint, prefer_read_url
from ..menu_tree import build_menu
from ..safety import annotate_catalog_item, is_write_blocked

router = APIRouter(tags=["setup"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Routes in this module are limited to what the DENON AVR MANAGER UI calls.

# Denon Input Assign posts each column to a dedicated ASP (not s_InputAssign.asp).
INPUT_ASSIGN_SUBMIT_PATHS = {
    "hdmi": "/SETUP/INPUTS/INPUTASSIGN/s_InputAssignHDMI.asp",
    "digital": "/SETUP/INPUTS/INPUTASSIGN/s_InputAssignDIGITAL.asp",
    "analog": "/SETUP/INPUTS/INPUTASSIGN/s_InputAssignANALOG.asp",
    "video": "/SETUP/INPUTS/INPUTASSIGN/s_InputAssignVIDEO.asp",
    "comp": "/SETUP/INPUTS/INPUTASSIGN/s_InputAssignCOMP.asp",
    "defaults": "/SETUP/INPUTS/INPUTASSIGN/s_InputAssign.asp",
}


class SubmitBody(BaseModel):
    fields: Dict[str, Any] = Field(
        ...,
        description="Form fields to POST. Merged over current page values when merge_defaults=true.",
    )
    merge_defaults: bool = True
    read_url: Optional[str] = Field(
        None,
        description="Override read URL used for defaults + verification",
    )
    assign_column: Optional[str] = Field(
        None,
        description=(
            "For Input Assign only: hdmi|digital|analog|video|comp|defaults — "
            "selects Denon's per-column submit ASP."
        ),
    )
    network_action: Optional[str] = Field(
        None,
        description=(
            "For Network pages: settings_save | connect — "
            "sets Denon Save/Connect flags and Connect submit path."
        ),
    )


class PowerBody(BaseModel):
    power: Optional[str] = Field(
        None,
        description="Main Zone power: on | standby. Omit with toggle=true.",
    )
    toggle: bool = Field(
        False,
        description="If true, switch between on and standby (ignores power).",
    )


def _default_base(request: Request) -> str:
    return request.app.state.default_host


def _client(request: Request) -> DenonSetupClient:
    """Always use DENON_HOST / app default — host is not selected from the UI."""
    return DenonSetupClient(_default_base(request))


def _probe(client: DenonSetupClient) -> Dict[str, Any]:
    """Cheap reachability check against SETUP home."""
    try:
        html = client.get("/SETUP/f_home.asp")
        ok = "SETUP" in html.upper() or "form" in html.lower() or len(html) > 200
        return {
            "reachable": bool(ok),
            "bytes": len(html),
            "probe_url": rewrite_url("/SETUP/f_home.asp", client.base),
        }
    except RuntimeError as e:
        return {
            "reachable": False,
            "error": str(e),
            "probe_url": rewrite_url("/SETUP/f_home.asp", client.base),
        }


# ---------- Connection status (env-configured host only) ----------


def _reject_if_standby(client: DenonSetupClient) -> None:
    """Block Setup / firmware writes while Main Zone is in Standby."""
    if main_zone_is_standby(client):
        raise HTTPException(
            403,
            {
                "error": "main_zone_standby",
                "message": STANDBY_SETTINGS_BLOCKED,
                "hint": "POST /api/power with power=on (or toggle) first.",
            },
        )


@router.get("/connection")
def get_connection(request: Request) -> Dict[str, Any]:
    base = _default_base(request)
    client = DenonSetupClient(base)
    probe = _probe(client)
    power: Dict[str, Any] = {}
    try:
        power = read_main_zone_power(client)
    except RuntimeError as e:
        power = {"error": str(e)}
    # Reachable if SETUP or goform power status works (standby still has network).
    reachable = bool(probe.get("reachable")) or power.get("power") in {
        "on",
        "standby",
    }
    return {
        "configured": True,
        "reachable": reachable,
        "probe": {
            "reachable": probe.get("reachable"),
            "error": probe.get("error"),
        },
        "power": {
            "power": power.get("power"),
            "power_on": power.get("power_on"),
            "zone": power.get("zone"),
            "input": power.get("input"),
            "error": power.get("error"),
        },
        "hint": "Set DENON_HOST in docker-compose.yml (environment) or the process environment.",
    }


# ---------- Main Zone power (goform HTTP — no telnet) ----------


@router.get("/power")
def get_power(request: Request) -> Dict[str, Any]:
    """Read Main Zone power / input via Denon goform XML (port 80)."""
    client = _client(request)
    try:
        status = read_main_zone_power(client)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    return scrub_host_urls(
        {
            **status,
            "read_at": _utc_now_iso(),
        }
    )


@router.post("/power")
def post_power(body: PowerBody, request: Request) -> Dict[str, Any]:
    """Set or toggle Main Zone power via formiPhoneAppDirect.xml (PWON / PWSTANDBY)."""
    client = _client(request)
    try:
        if body.toggle:
            result = toggle_main_zone_power(client)
        else:
            if not body.power:
                raise HTTPException(
                    400,
                    "Provide power='on'|'standby' or toggle=true",
                )
            result = set_main_zone_power(client, body.power)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    return scrub_host_urls(
        {
            **result,
            "read_at": _utc_now_iso(),
        }
    )


@router.get("/menu")
def menu(
    request: Request,
    include_extras: bool = Query(
        True,
        description="Include web-only pages not on the main OSD map (e.g. Bilingual Mode)",
    ),
) -> Dict[str, Any]:
    """SETUP menu in English-manual order (OSD hierarchy + web endpoint bindings)."""
    client = _client(request)
    data = build_menu(client.base, include_extras=include_extras)

    # Static / policy greys (blocked writes, amp-based Front Speaker)
    context: Dict[str, Any] = {}
    try:
        amp = client.read_page("/SETUP/SPEAKERS/AMPASSIGN/d_speakersetup.asp")
        fields = amp.get("fields") or {}
        context["amp_assign"] = (fields.get("listAmpAssignMode") or {}).get("value")
    except Exception:  # noqa: BLE001
        context["amp_assign"] = None
    flags = menu_inactive_flags(context)

    # Live greys straight from Denon's MENU/d_right_*.asp (Restorer, ZONE2, …)
    try:
        live = scrape_live_menu_availability(client)
        for mid, meta in live.items():
            if meta.get("inactive"):
                flags[mid] = meta
            elif mid not in flags:
                flags[mid] = meta
    except Exception:  # noqa: BLE001
        pass

    # Manual EQ: Denon greys when no content OR MultEQ XT is engaged
    multeq = None
    try:
        aud = client.read_page("/SETUP/AUDIO/AUDYSSEY/d_audio.asp")
        multeq = ((aud.get("fields") or {}).get("listRoomEq") or {}).get("value")
        context["multeq"] = multeq
    except Exception:  # noqa: BLE001
        context["multeq"] = None
    if multeq and str(multeq).upper() not in ("OFF", "", "0"):
        flags["audio_manual_eq"] = {
            "inactive": True,
            "inactive_reason": (
                "Manual EQ is available when MultEQ XT is Off and content is playing"
            ),
        }
    elif flags.get("audio_manual_eq", {}).get("inactive"):
        flags["audio_manual_eq"]["inactive_reason"] = (
            "Manual EQ is available when MultEQ XT is Off and content is playing"
        )

    # Clearer reasons for content-gated Audio items
    for mid, reason in (
        (
            "audio_dialog",
            "Dialog Level Adjust is available when compatible content is playing",
        ),
        (
            "audio_subwoofer",
            "Subwoofer Level Adjust is available when compatible content is playing",
        ),
        (
            "audio_restorer",
            "Restorer is available when a compressed PCM / compatible source is playing",
        ),
    ):
        if flags.get(mid, {}).get("inactive"):
            flags[mid]["inactive_reason"] = reason

    def apply_flags(nodes: List[Dict[str, Any]]) -> None:
        for n in nodes:
            fid = flags.get(n.get("id") or "")
            if fid:
                n["inactive"] = bool(fid.get("inactive"))
                if fid.get("inactive_reason"):
                    n["inactive_reason"] = fid["inactive_reason"]
                elif not n["inactive"]:
                    n.pop("inactive_reason", None)
            if n.get("children"):
                apply_flags(n["children"])

    apply_flags(data.get("sections") or [])

    setup_lock_on = False
    try:
        setup_lock_on = is_setup_locked(client)
    except Exception:  # noqa: BLE001
        setup_lock_on = False
    if setup_lock_on:
        apply_setup_lock_to_menu(data.get("sections") or [], True)

    data["context"] = {
        "amp_assign": context.get("amp_assign"),
        "setup_lock": setup_lock_on,
        "inactive_menu_ids": [
            k for k, v in flags.items() if v.get("inactive")
        ]
        if not setup_lock_on
        else ["*"],
    }
    return data


@router.get("/endpoints/{endpoint_id}/state")
def read_state(
    endpoint_id: str,
    request: Request,
) -> Dict[str, Any]:
    client = _client(request)
    try:
        item = annotate_catalog_item(get_endpoint(endpoint_id, client.base))
    except KeyError as e:
        raise HTTPException(404, f"Unknown endpoint_id: {endpoint_id}") from e
    read_url = prefer_read_url(item, client.base)
    if not read_url:
        raise HTTPException(400, "No read_url known for this endpoint")
    try:
        if endpoint_id == "audio_graphiceq_s_audio":
            state = client.read_page_stable(read_url)
        else:
            state = client.read_page(read_url)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    if isinstance(state.get("fields"), dict):
        fields = attach_field_labels(state["fields"])
        if endpoint_id == "general_information_s_information":
            html = client.get(read_url)
            fields = attach_field_labels(
                build_information_editor_fields(html, fields)
            )
        state["fields"] = layout_fields(fields, endpoint_id)
        state["page_inactive"] = not page_has_editable_controls(state["fields"])
        if state["page_inactive"]:
            state["page_inactive_reason"] = (
                "This page has no active controls for the current input / amp assign / "
                "signal. Denon greys it until the required setting is available."
            )
        # Setup Lock: freeze all pages except the lock toggle itself
        if endpoint_id != SETUP_LOCK_ENDPOINT_ID and is_setup_locked(client):
            for meta in state["fields"].values():
                if isinstance(meta, dict):
                    meta["inactive"] = True
                    meta["inactive_reason"] = SETUP_LOCK_REASON
            state["page_inactive"] = True
            state["page_inactive_reason"] = SETUP_LOCK_REASON
            state["setup_lock"] = True
        elif endpoint_id == SETUP_LOCK_ENDPOINT_ID:
            state["setup_lock"] = is_setup_locked(client)
    read_at = _utc_now_iso()
    if isinstance(state, dict):
        state["read_at"] = read_at
    return scrub_host_urls(
        {
            "endpoint_id": endpoint_id,
            "schema": item,
            "state": state,
            "read_at": read_at,
        }
    )


@router.post("/endpoints/{endpoint_id}")
def submit_endpoint(
    endpoint_id: str,
    body: SubmitBody,
    request: Request,
) -> Dict[str, Any]:
    client = _client(request)
    _reject_if_standby(client)
    try:
        item = get_endpoint(endpoint_id, client.base)
    except KeyError as e:
        raise HTTPException(404, f"Unknown endpoint_id: {endpoint_id}") from e

    blocked = is_write_blocked(endpoint_id, item.get("submit_url", ""))
    if blocked:
        raise HTTPException(
            403,
            {
                "error": "critical_write_blocked",
                "message": blocked,
                "endpoint_id": endpoint_id,
                "hint": "Writes blocked by safety policy.",
            },
        )

    if endpoint_id != SETUP_LOCK_ENDPOINT_ID and is_setup_locked(client):
        raise HTTPException(
            403,
            {
                "error": "setup_lock_active",
                "message": SETUP_LOCK_REASON,
                "endpoint_id": endpoint_id,
                "hint": "POST general_setuplock_s_general with radioSetupLock=OFF first.",
            },
        )

    read_url = body.read_url or prefer_read_url(item, client.base)
    if read_url:
        read_url = rewrite_url(read_url, client.base)

    submit_url = item["submit_url"]
    if body.assign_column:
        key = body.assign_column.strip().lower()
        if endpoint_id != "inputs_inputassign_s_inputassign":
            raise HTTPException(
                400, "assign_column is only valid for inputs_inputassign_s_inputassign"
            )
        path = INPUT_ASSIGN_SUBMIT_PATHS.get(key)
        if not path:
            raise HTTPException(
                400,
                f"Unknown assign_column '{body.assign_column}'. "
                f"Use one of: {', '.join(INPUT_ASSIGN_SUBMIT_PATHS)}",
            )
        submit_url = path

    fields = {k: str(v) for k, v in body.fields.items()}
    if body.network_action:
        action = body.network_action.strip().lower()
        if endpoint_id not in {
            "network_settings_s_network_setting_dhcp",
            "network_connection_s_network_setting_dhcp",
        }:
            raise HTTPException(
                400, "network_action is only valid for Network Settings/Connection"
            )
        if action == "settings_save":
            fields["buttonNetworkSettingDHCPSet"] = "DHCPSet"
            fields["buttonNetworkSettingProxySet"] = "ProxySet"
            fields["buttonNetworkSettingTestConnection"] = "off"
        elif action == "connect":
            fields["buttonNetworkSettingTestConnection"] = "TestConnection"
            fields["buttonNetworkSettingDHCPSet"] = "off"
            fields["buttonNetworkSettingProxySet"] = "off"
            submit_url = "/SETUP/NETWORK/CONNECTION/s_networkTestConnection.asp"
        else:
            raise HTTPException(
                400, "network_action must be settings_save or connect"
            )

    try:
        result = client.submit(
            submit_url,
            fields,
            read_url=read_url,
            merge_defaults=body.merge_defaults,
            endpoint_id=endpoint_id,
        )
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    after = result.get("after")
    if isinstance(after, dict) and isinstance(after.get("fields"), dict):
        fields = attach_field_labels(after["fields"])
        if endpoint_id == "general_information_s_information":
            read_url = prefer_read_url(
                annotate_catalog_item(get_endpoint(endpoint_id, client.base)),
                client.base,
            )
            if read_url:
                html = client.get(read_url)
                fields = attach_field_labels(
                    build_information_editor_fields(html, fields)
                )
        after["fields"] = layout_fields(fields, endpoint_id)
        after["read_at"] = _utc_now_iso()
        result["after"] = after
    read_at = _utc_now_iso()
    return scrub_host_urls(
        {
            "endpoint_id": endpoint_id,
            "write_allowed": True,
            "restored_safe_flags": True,
            "read_at": read_at,
            **result,
        }
    )


# ---------- Audyssey Setup engage stub (never starts wizard) ----------


@router.post("/speakers/audyssey-setup/engage")
def audyssey_setup_engage(
    confirm: bool = Query(
        False,
        description="Must be true to acknowledge; still does not start the wizard.",
    ),
) -> Dict[str, Any]:
    """Toggle/engage stub only — deliberately does not POST any wizard Start commands."""
    if not confirm:
        raise HTTPException(
            400,
            {
                "error": "confirm_required",
                "message": "Pass confirm=true to acknowledge. Wizard is still not started.",
            },
        )
    return {
        "engaged": True,
        "wizard_started": False,
        "actions_taken": [],
        "message": (
            "Engage acknowledged. No Audyssey Setup wizard steps were sent to the AVR. "
            "Use the receiver OSD / mic connection for actual calibration."
        ),
    }


# ---------- Firmware (UI buttons) ----------


@router.post("/firmware/actions/{action}", tags=["firmware"])
def firmware_action(
    action: str,
    request: Request,
    confirm: bool = Query(
        False,
        description="Must be true — acknowledges AVR may start network firmware check/update",
    ),
) -> Dict[str, Any]:
    """Trigger Update / Add New Feature / Web Update (matches Denon Firmware buttons)."""
    client = _client(request)
    _reject_if_standby(client)
    if is_setup_locked(client):
        raise HTTPException(
            403,
            {
                "error": "setup_lock_active",
                "message": SETUP_LOCK_REASON,
            },
        )
    if not confirm:
        raise HTTPException(
            400,
            {
                "error": "confirm_required",
                "message": "Pass confirm=true to run this firmware action on the AVR.",
                "action": action,
            },
        )
    if action not in FIRMWARE_ACTIONS:
        raise HTTPException(
            404,
            f"Unknown action '{action}'. Use one of: {', '.join(FIRMWARE_ACTIONS)}",
        )
    client = _client(request)
    # Add New Feature / update checks can take a while on the AVR
    timeout = 90.0 if action in ("update", "add_new_feature") else 30.0
    try:
        result = run_firmware_action(client, action, timeout=timeout)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e

    after = result.get("after")
    if isinstance(after, dict) and isinstance(after.get("fields"), dict):
        after["fields"] = layout_fields(
            attach_field_labels(after["fields"]),
            "general_firmware_s_firmware",
        )
        result["after"] = after

    return scrub_host_urls(
        {
            "write_allowed": True,
            "confirmed": True,
            **result,
        }
    )


@router.get("/firmware/local-upload/status", tags=["firmware"])
def firmware_local_upload_status(request: Request) -> Dict[str, Any]:
    """Whether Denon bootloader upload UI (bl_firmware_update.asp) is active."""
    try:
        return scrub_host_urls(local_upload_status(_client(request)))
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e


@router.post("/firmware/local-upload", tags=["firmware"])
async def firmware_local_upload(
    request: Request,
    file: UploadFile = File(..., description="Official Denon firmware package"),
    confirm: bool = Form(
        False,
        description="Must be true to post the file to the AVR",
    ),
    dry_run: bool = Form(
        False,
        description="If true, validate only — do not send anything to the AVR",
    ),
    enter_bootloader: bool = Form(
        True,
        description="If AVR is not in upload mode, trigger Web Update first",
    ),
) -> Dict[str, Any]:
    """Local firmware upload via /goform/formPostHandler (Denon bootloader form).

    Does nothing to the AVR unless confirm=true and dry_run=false.
    """
    if not confirm and not dry_run:
        raise HTTPException(
            400,
            {
                "error": "confirm_required",
                "message": (
                    "Pass confirm=true to upload, or dry_run=true to validate only. "
                    "Wrong firmware can brick the AVR."
                ),
            },
        )
    raw = await file.read()
    filename = file.filename or "firmware.bin"
    client = _client(request)
    if not dry_run and confirm:
        _reject_if_standby(client)
    try:
        result = upload_local_firmware(
            client,
            filename=filename,
            data=raw,
            content_type=file.content_type or "application/octet-stream",
            enter_bootloader_if_needed=enter_bootloader,
            dry_run=dry_run or not confirm,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    return scrub_host_urls(result)


@router.get("/info/dashboard", tags=["info"])
def info_dashboard(
    request: Request,
) -> Dict[str, Any]:
    """Human-readable Info cards (Network, Firmware, Audio/Video signal, Zones)."""
    try:
        return fetch_info_dashboard(_client(request))
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
