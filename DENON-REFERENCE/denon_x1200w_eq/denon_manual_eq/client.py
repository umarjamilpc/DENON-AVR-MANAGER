"""Denon AVR-X1200W Manual EQ (Graphic EQ) HTTP client.

Uses the SETUP web UI endpoints reverse-engineered from the live receiver.
See docs/PROTOCOL.md.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BANDS = (
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

BAND_FIELD = {b: f"textGEQ{b}" for b in BANDS}
BAND_LABEL = {
    "63": "63 Hz",
    "125": "125 Hz",
    "250": "250 Hz",
    "500": "500 Hz",
    "1k": "1 kHz",
    "2k": "2 kHz",
    "4k": "4 kHz",
    "8k": "8 kHz",
    "16k": "16 kHz",
}

SPEAKER_SELECTION = {
    "ALL": "All",
    "LRS": "Left/Right",
    "EAC": "Each",
}

MIN_DB = -20.0
MAX_DB = 6.0
STEP_DB = 0.5


class DenonManualEqError(RuntimeError):
    """Raised for protocol / validation failures."""


def _quantize_db(value: float) -> float:
    q = round(value / STEP_DB) * STEP_DB
    q = max(MIN_DB, min(MAX_DB, q))
    # Keep one decimal place for strings like 0.0 / -2.5
    return float(f"{q:.1f}")


def format_db(value: float) -> str:
    return f"{_quantize_db(value):.1f}"


@dataclass
class ManualEqState:
    enabled: bool
    speaker_selection: Optional[str] = None  # ALL / LRS / EAC
    channel: Optional[str] = None  # FL / FR / CEN / ...
    channels: Dict[str, str] = field(default_factory=dict)  # code -> label
    bands: Dict[str, float] = field(default_factory=dict)  # band key -> dB
    pure_direct: str = "OFF"
    setup_lock: str = "OFF"
    raw_html: str = ""


class DenonManualEqClient:
    """Read/write Manual EQ via SETUP GRAPHICEQ pages on port 80."""

    def __init__(
        self,
        host: str = "192.168.20.50",
        *,
        timeout: float = 15.0,
        settle_seconds: float = 1.0,
    ) -> None:
        self.host = host.rstrip("/")
        if self.host.startswith("http://") or self.host.startswith("https://"):
            self.base = self.host
        else:
            self.base = f"http://{self.host}"
        self.timeout = timeout
        self.settle_seconds = settle_seconds
        self.eq_path = "/SETUP/AUDIO/GRAPHICEQ"

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"{self.eq_path}/{path}"
        return f"{self.base}{path}"

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Mapping[str, str]] = None,
    ) -> str:
        body: Optional[bytes] = None
        headers = {
            "User-Agent": "denon-x1200w-eq/0.1",
            "Accept": "text/html,*/*",
        }
        if data is not None:
            body = urlencode(data).encode("ascii")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = Request(self._url(path), data=body, headers=headers, method=method)
        with urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def get_page(self) -> str:
        return self._request("GET", f"{self.eq_path}/d_audio.asp")

    def post(self, fields: Mapping[str, str]) -> str:
        html = self._request("POST", f"{self.eq_path}/s_audio.asp", fields)
        if self.settle_seconds:
            time.sleep(self.settle_seconds)
        return html

    @staticmethod
    def parse(html: str) -> ManualEqState:
        enabled = bool(
            re.search(
                r"name=['\"]radioGraphicEQ['\"]\s+value=['\"]ON['\"][^>]*checked",
                html,
                re.I,
            )
        )
        if not enabled:
            # also match checked before value (unlikely on this firmware)
            enabled = bool(
                re.search(
                    r"name=['\"]radioGraphicEQ['\"][^>]*checked[^>]*value=['\"]ON['\"]",
                    html,
                    re.I,
                )
            )

        def hidden(name: str, default: str = "OFF") -> str:
            m = re.search(
                rf"name=['\"]{re.escape(name)}['\"]\s+value=['\"]([^'\"]*)['\"]",
                html,
                re.I,
            )
            return m.group(1) if m else default

        speaker_selection = None
        m = re.search(
            r"name=['\"]listGEQSpSelection['\"][\s\S]*?</SELECT>",
            html,
            re.I,
        )
        if m:
            sm = re.search(
                r"value=['\"]([^'\"]+)['\"][^>]*selected",
                m.group(0),
                re.I,
            )
            if sm:
                speaker_selection = sm.group(1)

        channels: Dict[str, str] = {}
        channel = None
        m = re.search(
            r"name=['\"]listGEQAdjustEQ['\"][\s\S]*?</SELECT>",
            html,
            re.I,
        )
        if m:
            block = m.group(0)
            for om in re.finditer(
                r"<OPTION\s+value=['\"]([^'\"]+)['\"]([^>]*)>([^<]*)</OPTION>",
                block,
                re.I,
            ):
                code, attrs, label = om.group(1), om.group(2), om.group(3).strip()
                channels[code] = label
                if re.search(r"\bselected\b", attrs, re.I):
                    channel = code

        bands: Dict[str, float] = {}
        for band, field_name in BAND_FIELD.items():
            bm = re.search(
                rf"name=['\"]{re.escape(field_name)}['\"]\s+value=['\"]([^'\"]+)['\"]",
                html,
                re.I,
            )
            if bm:
                bands[band] = float(bm.group(1))

        return ManualEqState(
            enabled=enabled,
            speaker_selection=speaker_selection,
            channel=channel,
            channels=channels,
            bands=bands,
            pure_direct=hidden("setPureDirectOn", "OFF"),
            setup_lock=hidden("setSetupLock", "OFF"),
            raw_html=html,
        )

    def read(self) -> ManualEqState:
        return self.parse(self.get_page())

    def _base_fields(self, state: Optional[ManualEqState] = None) -> MutableMapping[str, str]:
        state = state or self.read()
        return {
            "setPureDirectOn": state.pure_direct or "OFF",
            "setSetupLock": state.setup_lock or "OFF",
            "setGEQCurveCopy": "off",
            "setGEQSetDefaults": "off",
            "setAdjustEQ": "off",
        }

    def set_enabled(self, enabled: bool) -> ManualEqState:
        fields = self._base_fields()
        fields["radioGraphicEQ"] = "ON" if enabled else "OFF"
        self.post(fields)
        return self.read()

    def select_channel(
        self,
        channel: str,
        *,
        speaker_selection: str = "EAC",
        ensure_enabled: bool = True,
    ) -> ManualEqState:
        channel = channel.upper()
        fields = self._base_fields()
        fields["radioGraphicEQ"] = "ON" if ensure_enabled else "OFF"
        fields["listGEQSpSelection"] = speaker_selection
        fields["listGEQAdjustEQ"] = channel
        self.post(fields)
        state = self.read()
        if ensure_enabled and not state.enabled:
            raise DenonManualEqError("Manual EQ did not stay enabled after channel select")
        if state.channel and state.channel.upper() != channel:
            raise DenonManualEqError(
                f"Expected channel {channel}, receiver shows {state.channel}"
            )
        return state

    def set_bands(
        self,
        channel: str,
        bands: Mapping[str, float],
        *,
        speaker_selection: str = "EAC",
        verify: bool = True,
    ) -> ManualEqState:
        """Apply a full 9-band curve to one channel.

        Missing bands are filled from the current channel reading.
        """
        channel = channel.upper()
        current = self.select_channel(channel, speaker_selection=speaker_selection)
        merged: Dict[str, float] = dict(current.bands)
        for key, value in bands.items():
            norm = key.lower().replace("hz", "").replace(" ", "")
            if norm.endswith("hz"):
                norm = norm[:-2]
            if norm not in BAND_FIELD:
                raise DenonManualEqError(f"Unknown band key: {key}")
            merged[norm] = _quantize_db(float(value))

        missing = [b for b in BANDS if b not in merged]
        if missing:
            raise DenonManualEqError(f"Incomplete band map, missing: {missing}")

        fields = self._base_fields(current)
        fields["radioGraphicEQ"] = "ON"
        fields["listGEQSpSelection"] = speaker_selection
        fields["listGEQAdjustEQ"] = channel
        for band in BANDS:
            fields[BAND_FIELD[band]] = format_db(merged[band])
        fields["setAdjustEQ"] = "Set"
        self.post(fields)

        state = self.read()
        if verify:
            for band in BANDS:
                got = state.bands.get(band)
                if got is None or abs(got - merged[band]) > 0.01:
                    raise DenonManualEqError(
                        f"Verify failed for {channel} {BAND_LABEL[band]}: "
                        f"wanted {merged[band]}, got {got}"
                    )
        return state

    def read_all_channels(
        self,
        channels: Optional[Iterable[str]] = None,
        *,
        speaker_selection: str = "EAC",
        restore_enabled: Optional[bool] = None,
        restore_channel: Optional[str] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Read bands for each channel. Restores prior enabled/channel if given."""
        before = self.read()
        if restore_enabled is None:
            restore_enabled = before.enabled
        if restore_channel is None:
            restore_channel = before.channel

        if not before.enabled:
            self.set_enabled(True)

        state = self.read()
        codes = list(channels) if channels is not None else list(state.channels.keys())
        out: Dict[str, Dict[str, float]] = {}
        for code in codes:
            ch = self.select_channel(code, speaker_selection=speaker_selection)
            out[code] = dict(ch.bands)

        # Restore previous Manual EQ enable + channel view
        if restore_channel:
            fields = self._base_fields()
            fields["radioGraphicEQ"] = "ON" if restore_enabled else "OFF"
            if restore_enabled:
                fields["listGEQSpSelection"] = speaker_selection
                fields["listGEQAdjustEQ"] = restore_channel
            self.post(fields)
        else:
            self.set_enabled(bool(restore_enabled))

        return out
