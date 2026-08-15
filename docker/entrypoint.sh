#!/bin/sh
# Make /data usable from the container AND from the host on any system.
#
# 1. Optional PUID/PGID (linuxserver-style) — run the app as your host user.
#    Defaults: 99:100 (Unraid nobody:users). Override on other systems with `id -u` / `id -g`.
# 2. Always chmod a+rwX on /data so host editors/SMB can modify settings files
#    even when ownership does not match.
set -e

PUID="${PUID:-99}"
PGID="${PGID:-100}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "[entrypoint] DENON_HOST=${DENON_HOST:-<not set>}"
echo "[entrypoint] LOG_LEVEL=${LOG_LEVEL}"
echo "[entrypoint] PUID=${PUID} PGID=${PGID}"

mkdir -p /data

# Best-effort ownership for the process user (may fail on some NFS/exotic FS).
chown -R "${PUID}:${PGID}" /data 2>/dev/null || true

# Always world read/write/execute-on-dirs so host + container both work.
chmod -R a+rwX /data 2>/dev/null || true

# If CMD is default uvicorn, inject --log-level from LOG_LEVEL env.
if [ "$1" = "uvicorn" ]; then
  shift
  exec su-exec "${PUID}:${PGID}" uvicorn "$@" --log-level "${LOG_LEVEL}"
fi

exec su-exec "${PUID}:${PGID}" "$@"
