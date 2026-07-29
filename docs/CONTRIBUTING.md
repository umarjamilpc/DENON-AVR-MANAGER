# Contributing

Thanks for helping improve **DENON AVR MANAGER**.

## Ground rules

1. **Do not commit secrets** — no `.env`, no real AVR passwords, no personal IPs in samples (use placeholders like `192.168.1.50`).  
2. **Do not credit Cursor / AI agent accounts as git authors** on commits you publish — use your own GitHub identity.  
3. **Safety first** — never add features that start Audyssey calibration, Maintenance Mode, or silent firmware flashes.  
4. **Restore probes** — if you toggle an AVR setting to scrape it, restore the previous value and document that in the PR.  
5. Prefer small, reviewable pull requests.

## Development setup

```bash
git clone https://github.com/umarjamilpc/DENON-AVR-MANAGER.git
cd DENON-AVR-MANAGER
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
export DENON_HOST=192.168.1.50
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Where to change what

| Goal | Start here |
|------|------------|
| New Setup page in the menu | `app/menu_tree.py` + ensure endpoint exists in `protocol/` |
| Field order / Set button / indent | `app/field_layout.py` |
| Display names | `app/field_labels.py` |
| Block or allow a write | `app/safety.py` |
| Parse odd HTML | `app/denon_client.py` |
| UI behaviour | `app/ui/assets/app.js` (+ bump `?v=` in `index.html`) |
| Re-scrape AVR | `tools/scrape_setup.py` → refresh `protocol/` |

## Adding a new page (checklist)

1. Confirm URLs with a browser on the AVR.  
2. Capture field names (View Source or Network tab).  
3. Update `protocol/endpoints.json` / re-run scrape tools.  
4. Add a leaf in `menu_tree.py`.  
5. Add `FIELD_ORDER` / enrichments if Denon’s layout needs help.  
6. Verify greys (parent radios, Setup Lock, content gates).  
7. Document anything surprising in `docs/PROTOCOL.md`.

## Docker changes

- Keep the final image **Alpine**-based and multi-arch capable.  
- Do not require a `.env` file — Compose `environment:` only.  
- Workflow: `.github/workflows/docker.yml`.

## Pull request tips

- Describe AVR model + firmware if behaviour is model-specific.  
- Include before/after screenshots for UI changes.  
- Note any temporary AVR setting changes and confirmation they were restored.

## Code of conduct (short)

Be respectful. This project controls real hardware — treat users’ receivers with care.
