"""MQTT volume scaling — expose dB range in HA (matches app UI), convert to/from Denon MV levels."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .denon_control import _db_str_to_mv, _mv_token_to_parts


def volume_uses_db(control: Dict[str, Any]) -> bool:
    kind = str(control.get("kind") or "")
    return kind in {"slider", "stepper"} and control.get("zero_db") is not None


def absolute_to_db(control: Dict[str, Any], absolute: int) -> float:
    zero = int(control.get("zero_db") or 80)
    return float(int(absolute) - zero)


def entity_to_db(control: Dict[str, Any], entity: Dict[str, Any]) -> Optional[float]:
    """Convert parsed entity to dB for MQTT state (handles half-steps via raw MV token)."""
    raw = str(entity.get("raw") or "").strip()
    prefix = str(control.get("prefix") or "MV").upper()
    if raw.upper().startswith(prefix):
        parts = _mv_token_to_parts(raw.upper().split()[0])
        if parts:
            return float(parts[2])
    val = entity.get("value")
    if val is None:
        return None
    try:
        return absolute_to_db(control, int(val))
    except (TypeError, ValueError):
        return None


def db_to_absolute(control: Dict[str, Any], value: Any) -> int:
    """Convert HA slider/command value (dB) to Denon absolute level for telnet."""
    try:
        db = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"volume value must be numeric dB, got {value!r}") from e
    parts = _db_str_to_mv(f"{db:g}")
    if parts is None:
        raise ValueError(f"invalid volume dB value: {value!r}")
    num, _raw, _db = parts
    lo = control.get("min")
    hi = control.get("max")
    if lo is not None and num < int(lo):
        raise ValueError(f"volume below min ({lo})")
    if hi is not None and num > int(hi):
        raise ValueError(f"volume above max ({hi})")
    return int(num)


def discovery_db_range(control: Dict[str, Any]) -> Dict[str, Any]:
    """HA number entity min/max/step in dB."""
    zero = int(control.get("zero_db") or 80)
    lo = int(control.get("min") if control.get("min") is not None else 0)
    hi = int(control.get("max") if control.get("max") is not None else 98)
    half = bool(control.get("half_step"))
    return {
        "min": float(lo - zero),
        "max": float(hi - zero),
        "step": 0.5 if half else 1.0,
        "unit_of_measurement": "dB",
    }
