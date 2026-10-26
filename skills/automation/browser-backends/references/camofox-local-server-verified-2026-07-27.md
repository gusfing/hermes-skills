# Camofox local server validated pattern — 2026-07-27

## Observed environment
- Linux container, Debian 13 `trixie`
- Node.js `v22.22.3`
- Package already present at `/opt/data/node_modules/@askjo/camofox-browser`
- Health endpoint reachable at `http://localhost:9377/health`

## Launch command
```bash
cd /opt/data/node_modules/@askjo/camofox-browser
CAMOFOX_PORT=9377 node server.js > /tmp/camofox-server.log 2>&1 &
sleep 3
curl -s http://localhost:9377/health
```

## Root cause of earlier false-negative
- Presence of `/usr/lib/x86_64-linux-gnu/libgtk-3.so.0` confirmed shared library exists
- Package presence check was wrong: missing `libgtk-3-0t64` from detection path
- `libgtk-3.so.0` symlink exists and points to real library

## Live validation before using through Hermes
Use REST API ground truth:
1. `POST /tabs` with `userId`/`sessionKey`
2. `GET /tabs/:tabId/snapshot?userId=...&includeScreenshot=true`
3. `GET /tabs?userId=...`
4. `POST /tabs/:tabId/navigate` with `@google_search`

Expected after successful launch:
```json
{"ok":true,"engine":"camoufox","browserConnected":true,"browserRunning":true,"activeTabs":0,"activeSessions":0}
```

## Session-specific note
- Browser launched under Xvfb virtual display successfully without `HOME=/root`
- Direct server launch worked after failed earlier `libgtk` package detection path
