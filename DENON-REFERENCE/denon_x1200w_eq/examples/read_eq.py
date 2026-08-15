#!/usr/bin/env python3
"""CLI for Denon X1200W Manual EQ.

Examples:
  python -m examples.read_eq --host 192.168.20.50
  python -m examples.read_eq --host 192.168.20.50 --all-channels
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from denon_manual_eq import BAND_LABEL, DenonManualEqClient


def main() -> int:
    p = argparse.ArgumentParser(description="Read Denon Manual EQ via SETUP web UI")
    p.add_argument("--host", default="192.168.20.50")
    p.add_argument(
        "--all-channels",
        action="store_true",
        help="Temporarily enable EQ if needed, dump every channel, then restore prior on/off",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    client = DenonManualEqClient(args.host)
    state = client.read()

    if args.all_channels:
        curves = client.read_all_channels()
        payload = {
            "enabled_after_restore": client.read().enabled,
            "channels": {
                code: {BAND_LABEL[b]: db for b, db in bands.items()}
                for code, bands in curves.items()
            },
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            for code, bands in curves.items():
                print(f"[{code}]")
                for b, db in bands.items():
                    print(f"  {BAND_LABEL[b]}: {db}")
        return 0

    payload = {
        "enabled": state.enabled,
        "speaker_selection": state.speaker_selection,
        "channel": state.channel,
        "channels": state.channels,
        "bands": {BAND_LABEL.get(k, k): v for k, v in state.bands.items()},
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Manual EQ: {'ON' if state.enabled else 'OFF'}")
        print(f"Speaker selection: {state.speaker_selection}")
        print(f"Channel: {state.channel} ({state.channels.get(state.channel or '', '')})")
        for k, v in state.bands.items():
            print(f"  {BAND_LABEL[k]}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
