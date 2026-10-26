#!/usr/bin/env bash
set -euo pipefail

PROFILE_DIR="${1:-/opt/data/chrome-profiles/wa_account_a}"
CDP_PORT="${2:-9222}"
DISPLAY_NUM="${3:-:99}"
UA="${4:-Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36}"

mkdir -p "$PROFILE_DIR"
rm -f "$PROFILE_DIR/SingletonLock" "$PROFILE_DIR/SingletonSocket*"

Xvfb "$DISPLAY_NUM" -screen 0 1280x720x24 >/tmp/xvfb-debug.log 2>&1 &
sleep 1
export DISPLAY="$DISPLAY_NUM"

BROWSER_BIN="${BROWSER_BIN:-/opt/data/.playwright/chromium-1234/chrome-linux64/chrome}"
"$BROWSER_BIN" \
  --no-sandbox \
  --disable-gpu \
  --remote-debugging-port="$CDP_PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --restore-last-session \
  --user-agent="$UA" \
  > /tmp/chrome-debug.log 2>&1 &

echo "Chrome PID=$!"
sleep 4
curl -s "http://127.0.0.1:${CDP_PORT}/json/version" || true
