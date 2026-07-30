from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from ..denon_client import DenonSetupClient
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
from ..info import (
    fetch_firmware_info,
    fetch_info_dashboard,
    fetch_network_info,
)
from ..protocol_loader import (
    catalog_for_host,
    get_endpoint,
    load_catalog,
    prefer_read_url,
)
from ..menu_tree import build_menu, cleaned_catalog
from ..safety import (
    annotate_catalog_item,
    catalog_filter_writable_only,
    is_write_blocked,
)

router = APIRouter(tags=["setup"])

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


@router.get("/connection")
def get_connection(request: Request) -> Dict[str, Any]:
    base = _default_base(request)
    client = DenonSetupClient(base)
    probe = _probe(client)
    return {
        "configured": True,
        "reachable": probe.get("reachable"),
        "probe": {
            "reachable": probe.get("reachable"),
            "error": probe.get("error"),
        },
        "hint": "Set DENON_HOST in docker-compose.yml (environment) or the process environment.",
    }


@router.post("/connection")
def set_connection_disabled() -> None:
    raise HTTPException(
        403,
        {
            "error": "host_locked",
            "message": "AVR host is managed via DENON_HOST (docker-compose / environment) — runtime IP changes are disabled.",
        },
    )


@router.get("/health")
def health(
    request: Request,
) -> Dict[str, Any]:
    client = _client(request)
    probe = _probe(client)
    return {
        "ok": True,
        "reachable": probe.get("reachable"),
        "host_source": "DENON_HOST",
        "policy": {
            "blocked_writes": [
                "firmware update / web update / add new feature",
                "save / load configuration",
                "setup lock",
                "network IP / DHCP / proxy changes",
                "Audyssey Setup mic wizard steps",
                "Maintenance Mode / Setup Assistant",
            ],
            "allowed_info_reads": ["firmware version", "network settings"],
            "audyssey_setup": "engage stub only — never starts wizard",
            "restore_policy": "Any probe that temporarily changes a setting must restore the prior value.",
        },
    }


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


@router.get("/catalog")
def catalog(
    request: Request,
    section: Optional[str] = Query(
        None,
        description="Filter by menu section label (Audio, Video, …) or raw folder",
    ),
    writable_only: bool = Query(
        False, description="If true, hide endpoints that are write-blocked"
    ),
    ordered: bool = Query(
        True,
        description="If true (default), return manual menu order with clean titles",
    ),
) -> Dict[str, Any]:
    client = _client(request)
    if ordered:
        items = cleaned_catalog(client.base)
        sections = [
            "Audio",
            "Video",
            "Inputs",
            "Speakers",
            "Network",
            "General",
        ]
        if section:
            key = section.strip().lower()
            items = [
                i
                for i in items
                if (i.get("menu_section") or i.get("section") or "").lower() == key
                or (i.get("section") or "").lower() == key
            ]
    else:
        items = catalog_for_host(client.base)
        if section:
            items = [i for i in items if i["section"].upper() == section.upper()]
        sections = sorted({i["section"] for i in load_catalog()})
    items = catalog_filter_writable_only(items, writable_only=writable_only)
    # Recreate titles after annotate when using cleaned list (annotate already done)
    return {
        "count": len(items),
        "sections": sections,
        "items": items,
        "menu": "/api/menu",
        "safety_note": (
            "Critical writes (firmware update, save/load, setup lock, network IP, "
            "Audyssey Setup wizard) are blocked. Catalog follows the English manual menu."
        ),
    }


@router.get("/endpoints/{endpoint_id}")
def endpoint_detail(
    endpoint_id: str,
    request: Request,
) -> Dict[str, Any]:
    client = _client(request)
    try:
        item = annotate_catalog_item(get_endpoint(endpoint_id, client.base))
    except KeyError as e:
        raise HTTPException(404, f"Unknown endpoint_id: {endpoint_id}") from e
    return item


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
    return scrub_host_urls(
        {
            "endpoint_id": endpoint_id,
            "schema": item,
            "state": state,
        }
    )


@router.post("/endpoints/{endpoint_id}")
def submit_endpoint(
    endpoint_id: str,
    body: SubmitBody,
    request: Request,
) -> Dict[str, Any]:
    client = _client(request)
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
                "hint": "Use /api/info/firmware or /api/info/network for read-only info.",
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
        result["after"] = after
    return scrub_host_urls(
        {
            "endpoint_id": endpoint_id,
            "write_allowed": True,
            "restored_safe_flags": True,
            **result,
        }
    )


# ---------- Audyssey Setup engage stub (never starts wizard) ----------


@router.get("/speakers/audyssey-setup")
def audyssey_setup_status() -> Dict[str, Any]:
    return {
        "id": "speakers_audyssey_setup_engage",
        "status": "stub",
        "engage_armed": False,
        "wizard_started": False,
        "note": (
            "Audyssey Setup is the mic calibration wizard (usually on-TV when the "
            "calibration mic is connected). This API never starts Begin Test / Next."
        ),
        "engage_path": "POST /api/speakers/audyssey-setup/engage",
        "write_allowed": False,
    }


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


# ---------- Read-only info ----------


@router.get("/firmware/actions", tags=["firmware"])
def list_firmware_actions() -> Dict[str, Any]:
    return {
        "actions": [
            {"id": k, "label": v["label"], "note": v["note"]}
            for k, v in FIRMWARE_ACTIONS.items()
        ]
    }


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


@router.get("/info/firmware", tags=["info"])
def info_firmware(
    request: Request,
) -> Dict[str, Any]:
    """Firmware version + notification state."""
    try:
        return fetch_firmware_info(_client(request))
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e


@router.get("/info/network", tags=["info"])
def info_network(
    request: Request,
) -> Dict[str, Any]:
    """Network DHCP/IP/DNS/proxy + friendly name + network standby (read-only)."""
    try:
        return fetch_network_info(_client(request))
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e


@router.get("/info/dashboard", tags=["info"])
def info_dashboard(
    request: Request,
) -> Dict[str, Any]:
    """Human-readable Info cards (Network, Firmware, Audio/Video signal, Zones)."""
    try:
        return fetch_info_dashboard(_client(request))
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e


# ---------- Convenience: Manual EQ ----------


class ManualEqBands(BaseModel):
    channel: str = Field("FL", description="FL/FR/CEN/SL/SR/TML/TMR")
    speaker_selection: str = Field("EAC", description="ALL / LRS / EAC")
    bands: Dict[str, float] = Field(
        ...,
        description="Keys: 63,125,250,500,1k,2k,4k,8k,16k — dB -20..+6 step 0.5",
    )
    enable: bool = True


class ManualEqAction(BaseModel):
    action: str = Field(..., description="curve_copy | set_defaults")
    channel: str = "FL"
    speaker_selection: str = "EAC"


class ManualEqSelect(BaseModel):
    """Switch Adjust EQ channel / Speaker Selection (Denon listBox submit)."""

    channel: str = "FL"
    speaker_selection: str = "EAC"


@router.get("/audio/manual-eq")
def get_manual_eq(
    request: Request,
) -> Dict[str, Any]:
    return read_state("audio_graphiceq_s_audio", request)


@router.post("/audio/manual-eq/select")
def select_manual_eq(
    payload: ManualEqSelect,
    request: Request,
) -> Dict[str, Any]:
    """Apply channel / speaker selection without writing band levels (listBox)."""
    fields: Dict[str, str] = {
        "radioGraphicEQ": "ON",
        "listGEQSpSelection": payload.speaker_selection,
        "listGEQAdjustEQ": payload.channel.upper(),
        "setAdjustEQ": "off",
        "setGEQCurveCopy": "off",
        "setGEQSetDefaults": "off",
    }
    body = SubmitBody(fields=fields, merge_defaults=True)
    return submit_endpoint("audio_graphiceq_s_audio", body, request)


@router.post("/audio/manual-eq/enable")
def set_manual_eq_enable(
    request: Request,
    enabled: bool = Query(...),
) -> Dict[str, Any]:
    """Toggle Manual EQ. Caller should restore prior On/Off if probing."""
    client = _client(request)
    before = client.read_page("/SETUP/AUDIO/GRAPHICEQ/d_audio.asp")
    prior = (before["fields"].get("radioGraphicEQ") or {}).get("value")
    body = SubmitBody(fields={"radioGraphicEQ": "ON" if enabled else "OFF"})
    result = submit_endpoint("audio_graphiceq_s_audio", body, request)
    result["prior_enabled"] = prior
    result["restore_hint"] = (
        f"POST /api/audio/manual-eq/enable?enabled={'true' if prior == 'ON' else 'false'}"
    )
    return result


@router.post("/audio/manual-eq/bands")
def set_manual_eq_bands(
    payload: ManualEqBands,
    request: Request,
) -> Dict[str, Any]:
    band_map = {
        "63": "textGEQ63",
        "125": "textGEQ125",
        "250": "textGEQ250",
        "500": "textGEQ500",
        "1k": "textGEQ1k",
        "2k": "textGEQ2k",
        "4k": "textGEQ4k",
        "8k": "textGEQ8k",
        "16k": "textGEQ16k",
    }
    fields: Dict[str, str] = {
        "radioGraphicEQ": "ON" if payload.enable else "OFF",
        "listGEQSpSelection": payload.speaker_selection,
        "listGEQAdjustEQ": payload.channel.upper(),
        "setAdjustEQ": "Set",
        "setGEQCurveCopy": "off",
        "setGEQSetDefaults": "off",
    }
    for key, form_name in band_map.items():
        if key not in payload.bands:
            raise HTTPException(400, f"Missing band '{key}' — send all 9 bands")
        # Keep ASCII signed dB (e.g. -2.5); never drop the leading minus.
        val = float(payload.bands[key])
        fields[form_name] = f"{val:.1f}"
    body = SubmitBody(fields=fields, merge_defaults=True)
    return submit_endpoint("audio_graphiceq_s_audio", body, request)


@router.post("/audio/manual-eq/action")
def manual_eq_action(
    payload: ManualEqAction,
    request: Request,
) -> Dict[str, Any]:
    """Curve Copy or Set Defaults (Manual EQ must already be On)."""
    action = (payload.action or "").strip().lower()
    if action not in ("curve_copy", "set_defaults"):
        raise HTTPException(400, "action must be curve_copy or set_defaults")
    fields: Dict[str, str] = {
        "radioGraphicEQ": "ON",
        "listGEQSpSelection": payload.speaker_selection,
        "listGEQAdjustEQ": payload.channel.upper(),
        "setAdjustEQ": "off",
        "setGEQCurveCopy": "Set" if action == "curve_copy" else "off",
        "setGEQSetDefaults": "Set" if action == "set_defaults" else "off",
    }
    body = SubmitBody(fields=fields, merge_defaults=True)
    return submit_endpoint("audio_graphiceq_s_audio", body, request)


@router.get("/resolve")
def resolve_url(
    request: Request,
    url: str = Query(..., description="Absolute or /SETUP/... path"),
) -> Dict[str, Any]:
    from urllib.parse import urlparse

    from ..denon_client import endpoint_id

    client = _client(request)
    catalog = catalog_for_host(client.base)
    matches = []
    path = urlparse(url).path if "://" in url else url
    needle_id = endpoint_id(url if "://" in url else f"http://x{path}")
    for item in catalog:
        annotated = annotate_catalog_item(item)
        candidates = [item["submit_url"], *item.get("read_urls", [])]
        for candidate in candidates:
            if url == candidate or urlparse(candidate).path == path:
                matches.append(
                    {
                        "id": annotated["id"],
                        "write_allowed": annotated["write_allowed"],
                        "write_block_reason": annotated["write_block_reason"],
                    }
                )
                break
            if endpoint_id(candidate) == needle_id:
                matches.append(
                    {
                        "id": annotated["id"],
                        "write_allowed": annotated["write_allowed"],
                        "write_block_reason": annotated["write_block_reason"],
                    }
                )
                break
    return {"url": url, "endpoint_ids": matches}


