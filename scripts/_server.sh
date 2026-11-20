# Shared by start.sh, stop.sh and restart.sh; sourced, never run on its own.
#
# The server runs from the repository root in the background:
#   - its pid is in data/golem-server.pid;
#   - its console output is appended to data/logs/server.out;
#   - its own log stays in data/logs/server.log.
# The port comes from GOLEM_PORT in the environment, then from GOLEM_PORT in .env, then 8700, as
# golem-server itself reads it. Nothing else is read from .env.

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$REPO/data/golem-server.pid"
OUT_FILE="$REPO/data/logs/server.out"

env_value() {
  # The last NAME=value line of .env, without quotes; empty when absent.
  local name="$1"
  [ -f "$REPO/.env" ] || return 0
  grep -E "^${name}=" "$REPO/.env" | tail -n 1 | cut -d= -f2- | tr -d "\"'" || true
}

PORT="${GOLEM_PORT:-$(env_value GOLEM_PORT)}"
PORT="${PORT:-8700}"
HOST="${GOLEM_HOST:-$(env_value GOLEM_HOST)}"
HOST="${HOST:-127.0.0.1}"
if [ "$HOST" = "::1" ]; then
  URL="http://[::1]:$PORT/"
else
  URL="http://$HOST:$PORT/"
fi

server_pid() {
  # The pid from the pid file when that process is still golem-server; empty otherwise.
  [ -f "$PID_FILE" ] || return 0
  local pid
  pid="$(cat "$PID_FILE")"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null \
      && ps -p "$pid" -o command= | grep -q "golem-server"; then
    echo "$pid"
  fi
}

port_in_use() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1
}

answers() {
  curl -s -o /dev/null --max-time 1 "${URL}api/levels"
}
