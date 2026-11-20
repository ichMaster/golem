#!/usr/bin/env bash
# Restart golem-server: stop, then start without opening a new browser tab. An open page shows
# "reconnecting…" and then continues the game where it was.
set -euo pipefail
here="$(dirname "$0")"
"$here/stop.sh"
"$here/start.sh" --no-open
