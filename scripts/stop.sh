#!/usr/bin/env bash
# Stop the golem-server that scripts/start.sh started. The human game is saved after every
# change, so the next start finds it where it was.
set -euo pipefail
source "$(dirname "$0")/_server.sh"

pid="$(server_pid)"
if [ -z "$pid" ]; then
  rm -f "$PID_FILE"
  echo "golem-server is not running (no live pid in $PID_FILE)"
  exit 0
fi

kill -TERM "$pid"
for _ in $(seq 1 40); do
  if ! kill -0 "$pid" 2>/dev/null; then
    break
  fi
  sleep 0.25
done
if kill -0 "$pid" 2>/dev/null; then
  echo "golem-server (pid $pid) did not stop in 10 s; killing it" >&2
  kill -KILL "$pid" 2>/dev/null || true
fi
rm -f "$PID_FILE"
echo "golem-server stopped (pid $pid)"
