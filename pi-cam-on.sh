#!/usr/bin/env bash
set -euo pipefail

# Tunables (override via env): WIDTH, HEIGHT, FPS, RETENTION_MIN, OUT_DIR
WIDTH=${WIDTH:-1280}
HEIGHT=${HEIGHT:-720}
FPS=${FPS:-30}
RETENTION_MIN=${RETENTION_MIN:-60}                # delete clips older than this (minutes)
OUT_DIR=${OUT_DIR:-"$HOME/video_out"}

STATE_DIR=${STATE_DIR:-"$HOME/.local/run/pi-cam"}
LOG_DIR=${LOG_DIR:-"$HOME/.local/share/pi-cam"}
mkdir -p "$OUT_DIR" "$STATE_DIR" "$LOG_DIR"

CAP_PGID_FILE="$STATE_DIR/capture.pgid"
CLN_PGID_FILE="$STATE_DIR/cleanup.pgid"

# Prevent double start
if [[ -f "$CAP_PGID_FILE" ]] && kill -0 -- -$(cat "$CAP_PGID_FILE") 2>/dev/null; then
  echo "Already running (PGID $(cat "$CAP_PGID_FILE"))."
  exit 0
fi

# Require tools
for cmd in rpicam-vid ffmpeg; do
  command -v "$cmd" >/dev/null || { echo "Missing $cmd. Install: sudo apt update && sudo apt install -y rpicam-apps ffmpeg"; exit 1; }
done

# Start capture in its own process group
setsid bash -c "
  exec >>'$LOG_DIR/capture.log' 2>&1
  echo \"[capture] starting at \$(date), saving to $OUT_DIR\"
  rpicam-vid -t 0 --nopreview --inline --width $WIDTH --height $HEIGHT --framerate $FPS -o - |
  ffmpeg -hide_banner -loglevel warning -f h264 -i - -c copy \
         -f segment -segment_time 60 -reset_timestamps 1 -movflags +faststart \
         -strftime 1 '$OUT_DIR/clip_%Y-%m-%d_%H-%M-%S.mp4'
" & CAP_LEADER=$!
echo $CAP_LEADER > "$CAP_PGID_FILE"

# Start cleanup loop in its own process group
setsid bash -c "
  exec >>'$LOG_DIR/cleanup.log' 2>&1
  echo \"[cleanup] keeping last $RETENTION_MIN minutes (started \$(date))\"
  while true; do
    find '$OUT_DIR' -type f -name '*.mp4' -mmin +$RETENTION_MIN -delete
    sleep 60
  done
" & CLN_LEADER=$!
echo $CLN_LEADER > "$CLN_PGID_FILE"

echo "✅ Recording ON. Clips: $OUT_DIR"
echo "Logs: $LOG_DIR (capture.log, cleanup.log)"
