# DENON AVR MANAGER — development compose

Use this file to test the **`dev`** branch image without touching production (`:latest`).

Production stays on:

```bash
docker compose up -d
# image: ghcr.io/umarjamilpc/denon-avr-manager:latest
```

## Run the dev build

```bash
# Optional: stop production first if it uses port 8000
# docker compose down

docker compose -f docker-compose.dev.yml pull
docker compose -f docker-compose.dev.yml up -d --force-recreate
```

UI: **http://127.0.0.1:8001/** (port **8001** so prod on 8000 can stay running)

Look for the **DEV** badge and top-bar **Realtime | Save** toggle.

## Switch back to production

```bash
docker compose -f docker-compose.dev.yml down
docker compose pull
docker compose up -d --force-recreate
```

## Image tags

| Branch | Image tag | Compose file |
|--------|-----------|--------------|
| `main` | `:latest` | `docker-compose.yml` |
| `dev` | `:dev` | `docker-compose.dev.yml` |

CI builds `:dev` on every push to the `dev` branch.
