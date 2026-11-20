#!/usr/bin/env bash
# Start golem-server in the background, wait until it answers, and open the game screen.
#
#   scripts/start.sh             start (or find running) and open the page in the browser
#   scripts/start.sh --no-open   the same without opening the browser
#
# Stop it with scripts/stop.sh; scripts/restart.sh does both.
set -euo pipefail
source "$(dirname "$0")/_server.sh"

open_page=1
for arg in "$@"; do
  case "$arg" in
    --no-open) open_page=0 ;;
    *) echo "usage: scripts/start.sh [--no-open]" >&2; exit 2 ;;
  esac
done

pid="$(server_pid)"
if [ -n "$pid" ]; then
  echo "golem-server is already running (pid $pid): $URL"
elif port_in_use; then
  echo "port $PORT is already in use by another process; stop it or set GOLEM_PORT" >&2
  exit 1
else
  mkdir -p "$REPO/data/logs"
  cd "$REPO"
  echo "--- $(date '+%Y-%m-%d %H:%M:%S') start" >>"$OUT_FILE"
  nohup uv run golem-server >>"$OUT_FILE" 2>&1 &
  pid=$!
  echo "$pid" >"$PID_FILE"
  for _ in $(seq 1 60); do
    if answers; then
      break
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      echo "golem-server did not start; its output ($OUT_FILE):" >&2
      # only this start's lines: everything after the last "--- … start" marker
      awk '/^--- .* start$/ { lines = "" } { lines = lines $0 "\n" } END { printf "%s", lines }' \
        "$OUT_FILE" | tail -n 15 >&2
      exit 1
    fi
    sleep 0.25
  done
  if ! answers; then
    echo "golem-server (pid $pid) does not answer at $URL yet; see $OUT_FILE" >&2
    exit 1
  fi
  echo "golem-server is running (pid $pid): $URL"
fi

if [ "$open_page" -eq 1 ] && command -v open >/dev/null 2>&1; then
  open "$URL"
fi
