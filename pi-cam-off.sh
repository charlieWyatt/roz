#!/usr/bin/env bash
set -euo pipefail

STATE_DIR=${STATE_DIR:-"$HOME/.local/run/pi-cam"}
CAP_PGID_FILE="$STATE_DIR/capture.pgid"
CLN_PGID_FILE="$STATE_DIR/cleanup.pgid"

stop_group() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  local pgid; pgid=$(cat "$file")
  if kill -0 -- -"$pgid" 2>/dev/null; then
    kill -- -"$pgid" 2>/dev/null || true
    for _ in {1..10}; do sleep 0.3; kill -0 -- -"$pgid" 2>/dev/null || break; done
    kill -9 -- -"$pgid" 2>/dev/null || true
    echo "Stopped PGID $pgid"
  fi
  rm -f "$file"
}

stop_group "$CAP_PGID_FILE"
stop_group "$CLN_PGID_FILE"
echo "🛑 Recording OFF."
