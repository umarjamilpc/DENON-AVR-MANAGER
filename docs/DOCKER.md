# Docker guide

## Why Alpine?

The image is based on **`python:3.12-alpine`** so the footprint stays small (good for Raspberry Pi and always-on NAS boxes). Dependencies are installed in a **multi-stage** build: compilers stay in the builder stage and are not shipped in the final image.

## Run with Compose (no `.env` file)

All runtime config is in `docker-compose.yml`:

```yaml
environment:
  DENON_HOST: "192.168.1.50"
volumes:
  - /mnt/user/appdata/UMAR-NAS-DENON-AVR-MANAGER:/data
```

| Variable | Required | Meaning |
|----------|----------|---------|
| `DENON_HOST` | **Yes** | AVR IP or hostname |

The `/data` volume keeps App Settings across container restarts. On first start the app creates `/data/app-settings.json` with defaults. On Unraid the host path is `/mnt/user/appdata/UMAR-NAS-DENON-AVR-MANAGER/`.

Port is fixed at **8000** inside the image. Map it on the host:

```yaml
ports:
  - "8000:8000"
```

## Pull and run (after the image is published)

```bash
docker pull ghcr.io/umarjamilpc/denon-avr-manager:latest
docker compose up -d
```

On first pull from GitHub Container Registry you may need to authenticate for private packages; for a **public** package, pull works anonymously.

Make the package public (GitHub → Packages → package settings) after the first successful Actions build if you want anonymous pulls.

## Multi-architecture (amd64 + arm64)

GitHub Actions workflow [`.github/workflows/docker.yml`](../.github/workflows/docker.yml):

- Uses **QEMU + Buildx**
- Builds `linux/amd64` and `linux/arm64`
- Pushes to `ghcr.io/umarjamilpc/denon-avr-manager`

Triggers:

- Push to `main`
- Version tags `v*` (e.g. `v1.0.0`)
- Manual **Actions → Build multi-arch Docker image → Run workflow**

You do **not** need Docker installed on your development PC for publishing — the cloud runner builds it.

## Build locally (optional)

Only if you have Docker:

```bash
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t denon-avr-manager:local --load .
# --load only loads one platform; for multi-arch prefer --push to a registry
```

Or single-arch for testing:

```bash
docker build -t denon-avr-manager:local .
docker run --rm -p 8000:8000 -e DENON_HOST=192.168.1.50 denon-avr-manager:local
```

## Networking notes

- The **container** must reach `DENON_HOST` on your LAN.
- Default bridge networking is fine when the Docker host can ping the AVR.
- On some NAS setups, use `network_mode: host` (Linux only) if bridge routing fails.

## Updating

```bash
docker compose pull
docker compose up -d
```
