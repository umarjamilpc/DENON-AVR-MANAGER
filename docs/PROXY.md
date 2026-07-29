# Reverse proxy (Nginx Proxy Manager)

DENON AVR MANAGER speaks plain **HTTP** on port **8000**.  
It is compatible with **HTTPS** when you terminate TLS in front (Nginx Proxy Manager, Caddy, Traefik, etc.). Users can use **HTTP and HTTPS** — the app does not force either.

## Recommended NPM setup

1. Run the container (`docker compose up -d`).
2. In Nginx Proxy Manager, add a **Proxy Host**:
   - **Domain**: e.g. `denon.home.lan` or `denon.example.com`
   - **Scheme**: `http`
   - **Forward hostname / IP**: Docker host IP or container name reachable from NPM
   - **Forward port**: `8000`
   - Enable **Websockets** (optional; not required today)
3. SSL tab: request Let’s Encrypt or use your cert for **HTTPS**.
4. Keep a second host (or access by IP) on **HTTP** if you want both.

Example:

| User opens | Reaches |
|------------|---------|
| `https://denon.home.lan/` | NPM → `http://AVR_MANAGER_HOST:8000/` |
| `http://192.168.1.10:8000/` | Direct to container (HTTP) |

## App behaviour

- UI is served at **`/`** (no `/ui`, no redirect, no `#` in the URL).
- API calls use **relative** paths (`/api/...`) so they work on `http://` and `https://`.
- Uvicorn runs with **`--proxy-headers`** so `X-Forwarded-Proto` / `X-Forwarded-For` from NPM are respected.

## Tips

- Prefer a **subdomain rooted at `/`**, not a path like `/denon/` (path prefixes need extra `root_path` config).
- Do not expose port 8000 to the public internet without auth / VPN; put auth on the NPM layer if needed.
