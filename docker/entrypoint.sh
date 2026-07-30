#!/bin/sh
# Make /data usable from the container AND from the host on any system.
#
# 1. Optional PUID/PGID (linuxserver-style) — run the app as your host user.
#    Defaults: 10001:10001 (image appuser).
#    Unraid tip: PUID=99 PGID=100 (nobody:users).
# 2. Always chmod a+rwX on /data so host editors/SMB can modify settings files
#    even when ownership does not match.
set -e

PUID="${PUID:-10001}"
PGID="${PGID:-10001}"

mkdir -p /data

# Best-effort ownership for the process user (may fail on some NFS/exotic FS).
chown -R "${PUID}:${PGID}" /data 2>/dev/null || true

# Always world read/write/execute-on-dirs so host + container both work.
chmod -R a+rwX /data 2>/dev/null || true

exec su-exec "${PUID}:${PGID}" "$@"
