# Reverse engineering the Denon SETUP web UI

This document explains **how** DENON AVR MANAGER discovered the AVR’s HTTP protocol so contributors can extend it safely.

## Background

| Interface | What it can do on AVR-X1200W |
|-----------|------------------------------|
| Telnet port **23** (official protocol PDF) | Power, volume, input, many sound modes — **not** per-band Manual EQ |
| SETUP website port **80** | Full Setup Menu including **Manual EQ (Graphic EQ)** bands |

The owner’s Manual EQ screen posts normal HTML forms. We captured those forms and mirrored them.

## Discovery steps (repeatable)

### 1. Confirm the web UI

```text
http://AVR_IP/SETUP/f_home.asp
```

Frameset menus live under `/SETUP/AUDIO/`, `/SETUP/VIDEO/`, …

### 2. Find Manual EQ

Path name is **GRAPHICEQ**; UI label is **Manual EQ**:

```text
GET  /SETUP/AUDIO/GRAPHICEQ/d_audio.asp     # read form
POST /SETUP/AUDIO/GRAPHICEQ/s_audio.asp     # submit
```

When EQ is **Off**, band sliders are absent. Temporarily set `radioGraphicEQ=ON`, read bands, then restore **Off**.

### 3. Capture a Set

Browser DevTools → Network → click **Set** on Manual EQ → copy form fields, e.g.:

- `textGEQ63` … `textGEQ16k` (−20.0 … +6.0, step 0.5)  
- `listGEQAdjustEQ` = channel (`FL`, `CEN`, …)  
- `setAdjustEQ=Set` to apply bands  

### 4. Crawl the rest of Setup (GET-first)

Script: `tools/scrape_setup.py`

- Starts from section frames + explicit seeds for greyed pages  
- Prefer **GET** only while mapping  
- Exclude Save/Load, firmware update posts, Maintenance, Setup Assistant, Audyssey wizard **Start**  
- Optional expand pass: toggle a setting, scrape, **restore** prior value  

Outputs land under `protocol/` (`endpoints.json`, `catalog.json`, `protocol_map.json`).

### 5. Align with the English manual

`tools/build_manual_coverage.py` + `protocol/MANUAL_COVERAGE.md` compare crawl results to the OSD Setup map (Audio → … → General).

## How the app uses the scrape

1. `protocol_loader` loads endpoint definitions.  
2. `denon_client.read_page` fetches live HTML and parses inputs.  
3. `attach_field_labels` + `layout_fields` make Denon-like labels/order/gates.  
4. `denon_client.submit` POSTs `application/x-www-form-urlencoded` with safety sanitization.

## Live greys

Denon marks unavailable submenu items as grey text **without** `<a href>` in:

```text
/SETUP/*/MENU/d_right_*.asp
```

`denon_menu_status.scrape_live_menu_availability()` mirrors that into `/api/menu`.

## Setup Lock behaviour

Denon: **General → Setup Lock**.  
We read `radioSetupLock`. When **ON**:

- Menu leaves (except Setup Lock) are marked inactive  
- UI redirects to Setup Lock  
- POSTs to other endpoints return **403**  

## Contributor rules for new probes

1. **Never** leave the AVR in a worse state — always restore toggles.  
2. **Never** start Audyssey Setup / Begin Test / Maintenance.  
3. Prefer documenting a new field in `protocol/` + `field_layout.py` over one-off scripts.  
4. Keep secrets out of the repo (`DENON_HOST` only via Compose/environment).  

See also [PROTOCOL.md](PROTOCOL.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
