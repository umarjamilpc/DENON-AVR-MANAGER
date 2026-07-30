# HTTP API overview

Interactive docs: **`/docs`** (Swagger) and **`/redoc`**.

Base URL example: `http://127.0.0.1:8000`

Routes are limited to what the DENON AVR MANAGER UI uses (no unused aliases).

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/app-settings` | Persistent manager settings + field descriptions |
| PUT | `/api/app-settings` | Save settings (`{"settings":{...}}`) to Docker volume JSON |
| POST | `/api/app-settings/reset` | Restore defaults and overwrite the settings file |
| GET | `/api/manual-eq/export` | Export all Manual EQ channels from the AVR’s live Adjust EQ list |
| POST | `/api/manual-eq/import` | Import Manual EQ JSON; **blocked** if Amp Assign differs; missing speakers skipped with warnings (`dry_run` optional) |
| GET | `/api/connection` | Connection status + Main Zone `power` snapshot |
| GET | `/api/power` | Main Zone power / input (goform HTTP, no telnet) |
| POST | `/api/power` | Set power (`{"power":"on"|"standby"}`) or `{"toggle":true}` |
| GET | `/api/menu` | Setup tree + inactive/grey flags + `setup_lock` |
| GET | `/api/endpoints/{id}/state` | Read page fields (`read_at` UTC ISO timestamp) |
| POST | `/api/endpoints/{id}` | Write fields — **403 if Main Zone is Standby** |
| GET | `/api/info/dashboard` | Read-only info cards |
| POST | `/api/speakers/audyssey-setup/engage?confirm=true` | Engage **stub only** (never starts wizard) |
| POST | `/api/firmware/actions/{action}?confirm=true` | Firmware Update / Add Feature / Web Update |
| GET | `/api/firmware/local-upload/status` | Bootloader upload availability |
| POST | `/api/firmware/local-upload` | Local firmware package upload |

## Host configuration

The AVR address is **only** taken from the **`DENON_HOST`** environment variable.  
Clients cannot change the host at runtime (by design).

## App settings (persistent)

Manager options (poll interval, EQ confirm time, theme, standby lock, confirmations, …) are stored in **`/data/app-settings.json`** on the Docker volume — **not** in the browser.

The file is **created automatically on container start** if missing (defaults). Compose mounts host  
`/mnt/user/appdata/UMAR-NAS-DENON-AVR-MANAGER` → `/data`  
so settings survive `docker compose pull` / recreate.

The entrypoint keeps `/data` **world read/write** (`chmod a+rwX`) and optional `PUID`/`PGID` so both the container and host users can edit `app-settings.json`.

## Response cleanup

`state.fields` omits AVR bookkeeping such as `setPureDirectOn` / `setSetupLock` / raw `setbtn*` / hidden inputs.  
Those are still injected on write by the safety layer when needed.

## Errors

| Code | Meaning |
|------|---------|
| 403 | Safety block, or Setup Lock is On |
| 404 | Unknown endpoint id |
| 502 | AVR HTTP error / timeout |

## Example (read Volume)

```bash
curl -s http://127.0.0.1:8000/api/endpoints/audio_volume_s_audio/state
```
