# Denon AVR-X1200W Manual EQ toolkit

Reverse-engineered from the live SETUP web UI at `http://192.168.20.50/SETUP/…`.

Telnet cannot adjust per-band EQ. The web form can. This folder wraps those HTTP calls.

## Status

| Item | Status |
|------|--------|
| Protocol capture | Done — see `docs/PROTOCOL.md` |
| Python client (read / enable / set bands) | Done — `denon_manual_eq/` |
| HA custom component | Not yet (next step) |

## Safety during probing (2026-07-29)

1. Snapshot: Manual EQ was **Off**, MultEQ/DynEQ/DynVol already **Off**.
2. Briefly set Manual EQ **On** only to read the band form (needed — Off page has no sliders).
3. Sampled Front L + Center curves (**no** `setAdjustEQ=Set` apply).
4. Restored Manual EQ to **Off**. Audyssey left Off.

Your Front L curve matched the screenshot (−2.5 / −0.5 / −1.0 / … / −5.0).

## Quick read (no writes)

```powershell
cd E:\CURSOR\HOME-ASSISTANT-MCP\integrations\denon_x1200w_eq
python examples\read_eq.py --host 192.168.20.50
```

If Manual EQ is Off, bands are empty in the response (UI hides them). Enable first, or use `--all-channels` (enables temporarily, reads each channel, restores prior On/Off).

## Apply a curve (writes)

```python
from denon_manual_eq import DenonManualEqClient

c = DenonManualEqClient("192.168.20.50")
c.set_bands(
    "FL",
    {
        "63": -2.5,
        "125": -0.5,
        "250": -1.0,
        "500": -0.5,
        "1k": 0.0,
        "2k": 0.0,
        "4k": -1.5,
        "8k": -3.0,
        "16k": -5.0,
    },
)
```

## Key endpoint

```text
POST http://192.168.20.50/SETUP/AUDIO/GRAPHICEQ/s_audio.asp
setAdjustEQ=Set
listGEQAdjustEQ=FL
textGEQ63=-2.5 ... textGEQ16k=-5.0
radioGraphicEQ=ON
listGEQSpSelection=EAC
```

## Layout

```text
denon_x1200w_eq/
  docs/PROTOCOL.md
  denon_manual_eq/client.py
  examples/read_eq.py
  captures/          # saved HTML from the live AVR
```
