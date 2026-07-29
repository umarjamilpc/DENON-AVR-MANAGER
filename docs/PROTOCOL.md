# Protocol reference (SETUP HTTP)

Validated on **AVR-X1200W** (GoAhead-Webs) over LAN HTTP.

## URL pattern

| Role | Pattern |
|------|---------|
| Section frameset | `/SETUP/<SECTION>/f_*.asp` |
| Form (read) | `/SETUP/.../d_*.asp` |
| Form (submit) | `/SETUP/.../s_*.asp` |
| Submenu (grey detection) | `/SETUP/<SECTION>/MENU/d_right_*.asp` |

## Common hidden fields

Every SETUP form typically includes:

| Field | Forced by this app on write |
|-------|-----------------------------|
| `setPureDirectOn` | `OFF` |
| `setSetupLock` | `OFF` (except on the Setup Lock page itself) |

Clients do not need to send these; `safety.sanitize_write_fields` injects them.

## Manual EQ (Graphic EQ)

| Item | Value |
|------|--------|
| Read | `GET /SETUP/AUDIO/GRAPHICEQ/d_audio.asp` |
| Write | `POST /SETUP/AUDIO/GRAPHICEQ/s_audio.asp` |
| Enable | `radioGraphicEQ=ON\|OFF` |
| Bands | `textGEQ63` … `textGEQ16k` |
| Channel view | `listGEQAdjustEQ` (`FL`, `FR`, `CEN`, `SL`, `SR`, `TML`, `TMR`, …) |
| Apply bands | `setAdjustEQ=Set` |
| Curve copy / defaults | `setGEQCurveCopy` / `setGEQSetDefaults` (button-gated) |

MultEQ XT must be **Off** for Manual EQ to be available.

## Endpoint IDs

Catalog IDs look like:

```text
audio_volume_s_audio
video_hdmisetup_s_video
speakers_crossovers_s_speakersetup
general_setuplock_s_general
```

Derived from the submit path (`s_*.asp`). Prefer `*_s_*` write endpoints over `*_r_*` read aliases.

## Machine-readable files

| File | Contents |
|------|----------|
| `protocol/endpoints.json` | Fields per submit URL |
| `protocol/catalog.json` | Flattened catalog |
| `protocol/protocol_map.json` | Full crawl map |
| `protocol/manual_coverage.json` | Manual checklist data |

## Tools

| Script | Purpose |
|--------|---------|
| `tools/scrape_setup.py` | GET-oriented SETUP crawler |
| `tools/enrich_protocol.py` | Merge Manual EQ ON-state fields |
| `tools/expand_forms_safe.py` | Safe expand + restore |
| `tools/build_manual_coverage.py` | Coverage report |

Always point tools at a lab AVR and restore settings after probes.
