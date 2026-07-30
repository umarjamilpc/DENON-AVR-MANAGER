# DENON AVR MANAGER

**Control your Denon AVR’s Setup Menu from a browser** — on a PC, NAS, or Raspberry Pi — using a small Docker container.

Validated on **Denon AVR-X1200W**. Other Denon/Marantz models that share the same SETUP web UI may work; see [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

**Repository:** [github.com/umarjamilpc/DENON-AVR-MANAGER](https://github.com/umarjamilpc/DENON-AVR-MANAGER)

---

## What is this?

Denon receivers expose a **Setup** website on your home network (Audio, Video, Speakers, Manual EQ, etc.).  
This project wraps that website into:

| Piece | What you get |
|--------|----------------|
| **Web UI** | Clean menu that mirrors Denon’s Setup structure |
| **HTTP API** | JSON read/write for Home Assistant, scripts, or other tools |
| **Safety rules** | Blocks dangerous actions (Save/Load dump, Audyssey mic wizard start, etc.) |

You do **not** need to install Python on the machine that runs it — **Docker Compose** is enough.

---

## Quick start (Docker — recommended)

### 1. Requirements

- A computer on the **same network** as the AVR (PC, Raspberry Pi, NAS, …)
- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- Your AVR’s **IP address** (from the receiver menu or your router)

### 2. Configure

Edit `docker-compose.yml` and set your AVR IP:

```yaml
environment:
  DENON_HOST: "192.168.1.50"   # ← change this
  PUID: "99"                   # optional; Unraid nobody (use `id -u` on Linux)
  PGID: "100"
volumes:
  - /mnt/user/appdata/UMAR-NAS-DENON-AVR-MANAGER:/data
```

There is **no `.env` file**. AVR host and volume paths live in `docker-compose.yml`.  
**App Settings** are auto-created as `/data/app-settings.json` on first start. The volume is kept world-readable/writable so you can edit that file from the host as well as from the Settings UI.

### 3. Run

```bash
docker compose up -d
```

### 4. Open the UI

In a browser: **http://127.0.0.1:8000/**  
API docs: **http://127.0.0.1:8000/docs**

Works behind **HTTP or HTTPS** reverse proxies (e.g. Nginx Proxy Manager) — see [docs/PROXY.md](docs/PROXY.md).


### 5. Stop

```bash
docker compose down
```

#### Multi-architecture image

The published image supports:

| Platform | Examples |
|----------|----------|
| **linux/amd64** | Most PCs, Intel/AMD NAS |
| **linux/arm64** | Raspberry Pi 4/5 (64-bit), many ARM SBCs |

Docker pulls the correct architecture automatically.

Image: `ghcr.io/umarjamilpc/denon-avr-manager:latest`  
(Published by GitHub Actions when this repo is pushed — see [docs/DOCKER.md](docs/DOCKER.md).)

---

## Run without Docker (developers)

```bash
export DENON_HOST=192.168.1.50          # Linux / macOS
# set DENON_HOST=192.168.1.50           # Windows PowerShell: $env:DENON_HOST="..."

python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## Safety (important)

The app **refuses** or carefully gates risky AVR operations:

- Configuration Save / Load dumps  
- Audyssey **Setup mic wizard** start (engage is a stub only)  
- Maintenance Mode / Setup Assistant  
- Network IP changes require an **explicit** Save (with warnings)  
- Firmware update actions require confirmation  

**Setup Lock** On/Off is supported; when Lock is On, other settings are greyed out until you unlock.

Details: [docs/SAFETY.md](docs/SAFETY.md)

---

## Documentation

| Doc | Audience |
|-----|----------|
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | First-time users |
| [docs/PROXY.md](docs/PROXY.md) | Nginx Proxy Manager / HTTPS + HTTP |
| [docs/UI_GUIDE.md](docs/UI_GUIDE.md) | Using the Setup Menu UI |
| [docs/API.md](docs/API.md) | HTTP API overview |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the code is organized |
| [docs/REVERSE_ENGINEERING.md](docs/REVERSE_ENGINEERING.md) | How the AVR web protocol was discovered |
| [docs/PROTOCOL.md](docs/PROTOCOL.md) | SETUP URLs, forms, Manual EQ |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | How to extend the app safely |
| [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) | Other models / caveats |
| [protocol/MANUAL_COVERAGE.md](protocol/MANUAL_COVERAGE.md) | Manual vs crawl checklist |

---

## Project layout

```text
DENON-AVR-MANAGER/
  app/                 # FastAPI app + browser UI
  protocol/            # Scraped endpoints / catalog (runtime data)
  tools/               # Contributor scrape / enrich scripts
  docs/                # Human documentation
  Dockerfile           # Alpine multi-stage image
  docker-compose.yml   # Run config (includes DENON_HOST)
  .github/workflows/   # Cloud build for amd64 + arm64
```

---

## License

MIT — see [LICENSE](LICENSE).

Denon and Audyssey are trademarks of their respective owners. This is an unofficial community project.
