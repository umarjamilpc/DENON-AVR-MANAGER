"""Manual EQ backup: export/import every channel from live AVR options.

Channel codes/labels come from the AVR's listGEQAdjustEQ options (Amp Assign
dependent). Never hard-code TML/TMR/etc.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .denon_client import DenonSetupClient
from .denon_power import main_zone_is_standby
from .protocol_loader import get_endpoint, prefer_read_url

EQ_ENDPOINT_ID = "audio_graphiceq_s_audio"
AMP_ENDPOINT_ID = "speakers_ampassign_s_speakersetup"
BACKUP_TYPE = "denon-manual-eq"
BACKUP_VERSION = 1

BAND_FIELDS: Tuple[str, ...] = (
    "textGEQ63",
    "textGEQ125",
    "textGEQ250",
    "textGEQ500",
    "textGEQ1k",
    "textGEQ2k",
    "textGEQ4k",
    "textGEQ8k",
    "textGEQ16k",
)

BAND_KEYS: Tuple[str, ...] = (
    "63",
    "125",
    "250",
    "500",
    "1k",
    "2k",
    "4k",
    "8k",
    "16k",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _field_value(fields: Mapping[str, Any], name: str) -> str:
    meta = fields.get(name)
    if isinstance(meta, dict):
        return str(meta.get("value") or "")
    if meta is None:
        return ""
    return str(meta)


def _option_list(fields: Mapping[str, Any], name: str) -> List[Dict[str, str]]:
    meta = fields.get(name)
    if not isinstance(meta, dict):
        return []
    out: List[Dict[str, str]] = []
    for opt in meta.get("options") or []:
        if isinstance(opt, dict):
            value = str(opt.get("value") or "").strip()
            if not value:
                continue
            label = str(opt.get("label") or opt.get("display") or value).strip()
            out.append({"value": value, "label": label or value})
        else:
            value = str(opt).strip()
            if value:
                out.append({"value": value, "label": value})
    return out


def _bands_from_fields(fields: Mapping[str, Any]) -> Dict[str, str]:
    bands: Dict[str, str] = {}
    for key, form_name in zip(BAND_KEYS, BAND_FIELDS):
        raw = _field_value(fields, form_name).strip()
        bands[key] = raw if raw else "0.0"
    return bands


def _bands_to_fields(bands: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, form_name in zip(BAND_KEYS, BAND_FIELDS):
        raw = bands.get(key)
        if raw is None:
            continue
        try:
            n = float(str(raw).replace("\u2212", "-").replace("\u2013", "-"))
            out[form_name] = f"{n:.1f}"
        except (TypeError, ValueError):
            out[form_name] = "0.0"
    return out


def _eq_urls() -> Tuple[str, str]:
    ep = get_endpoint(EQ_ENDPOINT_ID) or {}
    submit = str(ep.get("submit_url") or "")
    read = prefer_read_url(ep) or submit
    if not submit:
        raise RuntimeError(f"Unknown endpoint {EQ_ENDPOINT_ID}")
    return submit, read


def _amp_urls() -> Tuple[str, str]:
    ep = get_endpoint(AMP_ENDPOINT_ID) or {}
    submit = str(ep.get("submit_url") or "")
    read = prefer_read_url(ep) or submit
    if not submit:
        raise RuntimeError(f"Unknown endpoint {AMP_ENDPOINT_ID}")
    return submit, read


def read_amp_assign(client: DenonSetupClient) -> Dict[str, str]:
    _, read = _amp_urls()
    page = client.read_page(read)
    fields = page.get("fields") or {}
    value = _field_value(fields, "listAmpAssignMode")
    label = value
    for opt in _option_list(fields, "listAmpAssignMode"):
        if opt["value"] == value:
            label = opt["label"]
            break
    return {"value": value, "label": label}


def _require_main_on(client: DenonSetupClient) -> None:
    if main_zone_is_standby(client):
        raise RuntimeError(
            "Main Zone is on Standby — Power On before Manual EQ export/import."
        )


def _post_eq(client: DenonSetupClient, fields: Mapping[str, str]) -> Dict[str, Any]:
    submit, read = _eq_urls()
    return client.submit(
        submit,
        dict(fields),
        read_url=read,
        merge_defaults=True,
        endpoint_id=EQ_ENDPOINT_ID,
    )


def _pick_each_mode(sp_options: List[Dict[str, str]]) -> Optional[str]:
    """Resolve Speaker Selection 'Each' from live AVR options (not hard-coded)."""
    for opt in sp_options:
        if opt["value"].upper() == "EAC":
            return opt["value"]
    for opt in sp_options:
        if "each" in opt["label"].lower():
            return opt["value"]
    return None


def _select_channel(
    client: DenonSetupClient, *, channel: str, speaker_selection: str
) -> Dict[str, Any]:
    """Denon listBox: change channel without Set so AVR loads that curve."""
    _post_eq(
        client,
        {
            "radioGraphicEQ": "ON",
            "listGEQSpSelection": speaker_selection,
            "listGEQAdjustEQ": channel,
            "setAdjustEQ": "off",
            "setGEQCurveCopy": "off",
            "setGEQSetDefaults": "off",
        },
    )
    time.sleep(0.45)
    _, read = _eq_urls()
    return client.read_page_stable(read)


def _ensure_eq_on_each(client: DenonSetupClient) -> Tuple[Dict[str, Any], str]:
    """Turn Manual EQ On and Speaker Selection Each; return (stable page, each_code)."""
    _, read = _eq_urls()
    page = client.read_page_stable(read)
    fields = page.get("fields") or {}
    each = _pick_each_mode(_option_list(fields, "listGEQSpSelection"))
    if not each:
        raise RuntimeError(
            "Speaker Selection has no Each mode on this AVR — cannot address per-channel curves"
        )
    posted = _post_eq(
        client,
        {
            "radioGraphicEQ": "ON",
            "listGEQSpSelection": each,
            "setAdjustEQ": "off",
            "setGEQCurveCopy": "off",
            "setGEQSetDefaults": "off",
        },
    )
    time.sleep(0.35)
    after = posted.get("after") if isinstance(posted.get("after"), dict) else None
    if after and after.get("fields"):
        return after, each
    return client.read_page_stable(read), each


def live_channel_options(client: DenonSetupClient) -> Tuple[List[Dict[str, str]], str]:
    """Channel list from AVR after forcing Each mode (Amp Assign aware)."""
    page, each = _ensure_eq_on_each(client)
    fields = page.get("fields") or {}
    opts = _option_list(fields, "listGEQAdjustEQ")
    if not opts:
        raise RuntimeError(
            "AVR returned no Manual EQ channels. Check Amp Assign / MultEQ Off / not Direct."
        )
    return opts, each


def export_manual_eq(client: DenonSetupClient) -> Dict[str, Any]:
    """Read every live EQ channel curve into a portable backup object."""
    _require_main_on(client)
    amp = read_amp_assign(client)
    channels_meta, each = live_channel_options(client)
    channels: Dict[str, Any] = {}
    errors: List[Dict[str, str]] = []

    for opt in channels_meta:
        code = opt["value"]
        try:
            page = _select_channel(client, channel=code, speaker_selection=each)
            fields = page.get("fields") or {}
            got_ch = _field_value(fields, "listGEQAdjustEQ")
            if got_ch and got_ch != code:
                # One retry if AVR lagged.
                time.sleep(0.5)
                page = _select_channel(client, channel=code, speaker_selection=each)
                fields = page.get("fields") or {}
            channels[code] = {
                "label": opt["label"],
                "bands": _bands_from_fields(fields),
            }
        except Exception as exc:  # noqa: BLE001 — collect per-channel failures
            errors.append({"channel": code, "error": str(exc)})

    return {
        "type": BACKUP_TYPE,
        "version": BACKUP_VERSION,
        "exported_at": _utc_now(),
        "amp_assign": amp,
        "graphic_eq": "ON",
        "speaker_selection": each,
        "channels": channels,
        "channel_order": [o["value"] for o in channels_meta],
        "warnings": errors,
    }


def validate_backup(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Backup must be a JSON object")
    if raw.get("type") != BACKUP_TYPE:
        raise ValueError(f"Unsupported backup type (expected {BACKUP_TYPE})")
    try:
        ver = int(raw.get("version") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid backup version") from exc
    if ver != BACKUP_VERSION:
        raise ValueError(f"Unsupported backup version {ver}")
    channels = raw.get("channels")
    if not isinstance(channels, dict) or not channels:
        raise ValueError("Backup has no channels")
    amp = raw.get("amp_assign")
    if not isinstance(amp, dict) or not str(amp.get("value") or "").strip():
        raise ValueError("Backup missing amp_assign.value")
    return raw


def import_manual_eq(
    client: DenonSetupClient,
    backup: Mapping[str, Any],
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Restore channel curves. Refuses if Amp Assign differs; skips missing speakers."""
    _require_main_on(client)
    data = validate_backup(dict(backup))
    current_amp = read_amp_assign(client)
    file_amp = str((data.get("amp_assign") or {}).get("value") or "")
    if current_amp.get("value") != file_amp:
        raise RuntimeError(
            "Amp Assign differs — import blocked. "
            f"File={file_amp or '?'} ({(data.get('amp_assign') or {}).get('label') or ''}), "
            f"AVR={current_amp.get('value') or '?'} ({current_amp.get('label') or ''}). "
            "Match Amp Assign first, then import again."
        )

    live_opts, each = live_channel_options(client)
    live_codes = {o["value"] for o in live_opts}
    live_labels = {o["value"]: o["label"] for o in live_opts}
    file_channels: Dict[str, Any] = dict(data.get("channels") or {})

    missing = sorted(code for code in file_channels if code not in live_codes)
    will_import = sorted(code for code in file_channels if code in live_codes)
    warnings = [
        {
            "channel": code,
            "message": (
                f"Speaker '{code}' is in the file but not on the AVR now "
                f"(Amp Assign / Speaker Config) — skipped."
            ),
        }
        for code in missing
    ]

    report: Dict[str, Any] = {
        "dry_run": dry_run,
        "amp_assign": current_amp,
        "speaker_selection": each,
        "will_import": will_import,
        "skipped_missing": missing,
        "warnings": warnings,
        "imported": [],
        "failed": [],
    }
    if dry_run:
        report["ok"] = True
        report["message"] = (
            f"Dry run: would import {len(will_import)} channel(s); "
            f"skip {len(missing)} missing."
        )
        return report

    if not will_import:
        report["ok"] = False
        report["message"] = "No matching channels to import."
        return report

    for code in will_import:
        entry = file_channels.get(code) or {}
        bands = entry.get("bands") if isinstance(entry, dict) else None
        if not isinstance(bands, dict):
            report["failed"].append({"channel": code, "error": "Missing bands"})
            continue
        try:
            payload = {
                "radioGraphicEQ": "ON",
                "listGEQSpSelection": each,
                "listGEQAdjustEQ": code,
                "setAdjustEQ": "Set",
                "setGEQCurveCopy": "off",
                "setGEQSetDefaults": "off",
                **_bands_to_fields(bands),
            }
            _post_eq(client, payload)
            time.sleep(0.55)
            page = _select_channel(client, channel=code, speaker_selection=each)
            got = _bands_from_fields(page.get("fields") or {})
            report["imported"].append(
                {
                    "channel": code,
                    "label": live_labels.get(code) or entry.get("label") or code,
                    "bands": got,
                }
            )
        except Exception as exc:  # noqa: BLE001
            report["failed"].append({"channel": code, "error": str(exc)})

    report["ok"] = not report["failed"]
    report["message"] = (
        f"Imported {len(report['imported'])} channel(s); "
        f"skipped {len(missing)} missing; "
        f"failed {len(report['failed'])}."
    )
    return report
