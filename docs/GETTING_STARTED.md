# Getting started

## What you need

1. A Denon AVR on your Wi‑Fi / Ethernet (tested: **AVR-X1200W**).
2. The AVR’s **IP address** (example: `192.168.1.50`).
3. A machine that can reach that IP (same home network).
4. Docker Desktop (Windows/Mac) or Docker Engine + Compose (Linux / Raspberry Pi OS).

## Find the AVR IP

On the receiver:

- Setup → Network → Information / Connection, **or**
- Check your router’s DHCP client list for “Denon”.

Open `http://YOUR_AVR_IP/` in a browser. If you see Denon’s web UI, the IP is correct.

## Install with Compose

1. Clone this repository (or copy the folder `DENON-AVR-MANAGER`).
2. Open `docker-compose.yml`.
3. Change:

   ```yaml
   DENON_HOST: "192.168.1.50"
   ```

   to your IP.

   App Settings (poll rate, theme, etc.) are stored under the mounted volume
   `/mnt/user/appdata/UMAR-NAS-DENON-AVR-MANAGER/` (see `docker-compose.yml`).
4. In a terminal, from this folder:

   ```bash
   docker compose up -d
   ```

5. Visit **http://127.0.0.1:8000/**

## First visit checklist

- Status should say the AVR is reachable.
- Open **Audio → Volume** and confirm values load.
- Prefer **Ctrl+F5** (hard refresh) after updates.

## Common problems

| Symptom | Fix |
|---------|-----|
| Container exits immediately | `DENON_HOST` missing/invalid — check compose `environment` |
| “Unreachable” | PC/Pi and AVR not on same LAN; firewall; wrong IP |
| UI looks old | Hard refresh; confirm you use port **8000** (or the port you mapped) |
| Raspberry Pi “exec format” | Use the multi-arch image from GHCR (not an amd64-only local build) |

More Docker help: [DOCKER.md](DOCKER.md).
