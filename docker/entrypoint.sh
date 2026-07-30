#!/bin/sh
# Ensure the mounted /data volume is writable by appuser (UID 10001).
# Unraid appdata binds often start owned by root/nobody → Permission denied otherwise.
set -e
mkdir -p /data
if chown -R appuser:appuser /data 2>/dev/null; then
  :
else
  # Last resort on stubborn mounts (still better than failing Save silently).
  chmod -R a+rwX /data 2>/dev/null || true
fi
exec su-exec appuser "$@"
