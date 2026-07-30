# Multi-stage Alpine build — small image for amd64 + arm64 (x86 PC and Raspberry Pi).
# Build locally (optional): docker buildx build --platform linux/amd64,linux/arm64 -t denon-avr-manager .
# CI publishes to ghcr.io/umarjamilpc/denon-avr-manager (see .github/workflows/docker.yml).

FROM python:3.12-alpine AS builder

RUN apk add --no-cache gcc musl-dev libffi-dev
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.12-alpine

LABEL org.opencontainers.image.title="DENON AVR MANAGER" \
      org.opencontainers.image.description="Web UI + API for Denon AVR SETUP (Alpine, multi-arch)" \
      org.opencontainers.image.source="https://github.com/umarjamilpc/DENON-AVR-MANAGER" \
      org.opencontainers.image.licenses="MIT"

RUN apk add --no-cache libffi su-exec \
    && adduser -D -H -u 10001 appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app ./app
COPY protocol ./protocol
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PUID=99 \
    PGID=100

# DENON_HOST must be provided at runtime (docker compose environment).
EXPOSE 8000

# Entrypoint runs as root briefly to fix /data perms (rw for container + host),
# then drops to PUID:PGID.
USER root
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
