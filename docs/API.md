# HTTP API overview

Interactive docs: **`/docs`** (Swagger) and **`/redoc`**.

Base URL example: `http://127.0.0.1:8000`

## Essentials

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Reachability + safety policy summary |
| GET | `/api/connection` | Connection status for `DENON_HOST` |
| GET | `/api/menu` | Setup tree (manual order) + inactive flags + `setup_lock` |
| GET | `/api/catalog` | Flat list of endpoints |
| GET | `/api/endpoints/{id}/state` | Read page fields (labels, gates, Set buttons) |
| POST | `/api/endpoints/{id}` | Write fields (`{"fields":{...},"merge_defaults":true}`) |
| GET | `/api/info/dashboard` | Read-only info cards |
| GET/POST | `/api/audio/manual-eq*` | Manual EQ helpers |
| GET/POST | `/api/speakers/audyssey-setup*` | Engage **stub only** (never starts wizard) |

## Host configuration

The AVR address is **only** taken from the **`DENON_HOST`** environment variable.  
Clients cannot change the host at runtime (by design).

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
