# Architecture

## High-level flow

```text
Browser UI  ──JSON──►  FastAPI (app/)  ──HTTP form──►  Denon AVR SETUP web UI
                             │
                             ├── protocol/*.json   (scraped endpoint catalog)
                             ├── field_layout.py   (order, gates, Set buttons)
                             ├── field_labels.py   (human labels)
                             ├── safety.py         (write blocks / forced fields)
                             └── denon_menu_status.py (live grey menus + Setup Lock)
```

## Main modules (`app/`)

| File | Role |
|------|------|
| `main.py` | FastAPI app, static UI, requires `DENON_HOST` |
| `denon_client.py` | GET page HTML, parse fields, POST forms |
| `protocol_loader.py` | Load `protocol/endpoints.json` + catalog |
| `menu_tree.py` | English-manual Setup hierarchy |
| `field_layout.py` | Field order, parent/child gates, enrichments |
| `field_labels.py` | Display names / clean text |
| `safety.py` | Blocked writes, forced Pure Direct / Setup Lock flags |
| `denon_menu_status.py` | Live inactive menus; Setup Lock enforcement helpers |
| `routers/setup.py` | All `/api/*` routes |
| `ui/` | Single-page Setup UI (`index.html`, `app.js`, `styles.css`) |

## Runtime data (`protocol/`)

Produced by scrape tools (see [REVERSE_ENGINEERING.md](REVERSE_ENGINEERING.md)):

- `endpoints.json` — submit URLs + field schemas  
- `catalog.json` — UI-friendly endpoint list  
- `protocol_map.json` — broader crawl map  
- `MANUAL_COVERAGE.md` — checklist vs owner’s manual  

## Design choices

1. **Talk to the AVR the same way the official web UI does** (HTML forms on port 80), not invent a private binary protocol.  
2. **Telnet** (`:23`) is incomplete for Manual EQ bands — web SETUP is required.  
3. **No `.env` in production path** — Compose / process environment only.  
4. **Safety first** — refuse operations that brick, lock out, or start calibration wizards.
