# DENON AVR MANAGER

HTTP API and embedded browser UI for Denon AVR SETUP pages (validated on **AVR-X1200W**).
AVR address is configured only via **`DENON_HOST`** in `.env` (or the process environment).

## Limits (enforced)

- No Save / Load configuration
- Network → Settings / Connection writable with **explicit Save/Connect only** (no live apply; confirm warns about disconnect)
- Firmware: Notifications + Update / Add New Feature / Web Update + Local Upload UI
- Setup Lock On/Off — toggle only (**no PIN on X1200W**)
- Information page layout matches Denon; **Notification Alerts** On/Off writable
- No Save/Load configuration dump; Audyssey wizard still stub-only
- No Audyssey Setup mic wizard start (`/api/speakers/audyssey-setup/engage` is a stub only)
- No runtime AVR IP changes from the UI/API

## Run

```powershell
cd E:\CURSOR\HOME-ASSISTANT-MCP\integrations\denon_x1200w_api
copy .env.example .env
# edit DENON_HOST=your.avr.ip
python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

Open: **http://127.0.0.1:8010/ui** · Docs: http://127.0.0.1:8010/docs

## Main API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/connection` | Reachability for env-configured host |
| GET | `/api/menu` | SETUP tree (manual order) |
| GET | `/api/catalog` | Flat leaves with clean titles |
| GET/POST | `/api/endpoints/{id}` | Read state / apply fields |
| GET | `/api/info/dashboard` | Human-readable Info pages |
| GET/POST | `/api/audio/manual-eq*` | Manual EQ helpers |
| GET/POST | `/api/speakers/audyssey-setup*` | Engage stub only |

Protocol dumps live under `protocol/`.
