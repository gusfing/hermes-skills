# Camofox Operational Lifecycle

**Last verified:** 2026-08-31 on Oracle Linux 9.8 aarch64, Camofox v1.13.1

## Process model: wrapper vs real server

`npm start` in `@askjo/camofox-browser` launches via a wrapper shell (`server.js`).
When started via `nohup npm start > log 2>&1 &`:

- The **wrapper** (`nohup ... &`) prints a PID and exits quickly. That PID is NOT
  the server — it's the shell that launched it.
- The **real server** is a child `node server.js` process that stays running.
- Do not interpret the wrapper's exit as the server dying. Check the real process.

## Health checks (do these, in order)

```bash
# 1. Is port 9377 listening?
ss -tlnp | grep 9377

# 2. Is there a node process serving it?
ps aux | grep 'node server.js' | grep -v grep

# 3. Is the browser pre-warmed? (log says "browser pre-warmed")
tail -5 /tmp/camofox.log

# 4. Can you create a tab? (real integration test)
curl -s -X POST http://localhost:9377/tabs \
  -H 'Content-Type: application/json' \
  -d '{"userId":"test","sessionKey":"test","url":"https://example.com"}' | python3 -m json.tool
```

**Do NOT use `GET /ready` — it does not exist.** The server returns
`Cannot GET /ready`. The health endpoint is the port being open + browser
pre-warmed + tab creation working.

## What a restart loses

When Camofox restarts (crash, kill, or manual restart):

- **All imported cookies are lost.** The browser profile is fresh.
- **All session state is lost.** Previously imported LinkedIn/X/ChatGPT cookies
  must be re-imported via `POST /sessions/{userId}/cookies`.
- **Tab IDs from before the restart are dead.** New tabs get new IDs.
- **Previously saved `sessionKey`/`userId` pairs still work** as identifiers,
  but the browser state inside them is empty until cookies are re-imported.

**Mitigation:** keep cookie exports backed up (e.g.
`~/.hermes/outreach/linkedin-cookies.json`) so re-import is fast after a restart.

## Log locations

- Camofox server log: `/tmp/camofox.log` (or wherever `npm start` redirects)
- Camoufox browser binary: `~/.cache/camoufox/camoufox-bin`
- Profiles: `/home/opc/.camofox/profiles`

## Common log lines and what they mean

| Log line | Meaning |
|---|---|
| `"server started","port":9377` | REST API is up, accepting connections |
| `"browser pre-warmed","ms":...` | Browser launched and ready for tabs |
| `"port in use", "port": 9377` | Another Camofox instance already bound to 9377 — kill it first |
| `"camoufox launched"` | Browser binary started OK |
| `"xvfb not available, falling back to headless"` | Normal on headless servers; not an error |

## Fast "is it up?" one-liner

```bash
ss -tlnp | grep -q 9377 && echo "PORT OPEN" || echo "PORT CLOSED"
tail -1 /tmp/camofox.log | grep -q "browser pre-warmed" && echo "BROWSER READY" || echo "BROWSER NOT READY"
```

## When Camofox is down and you need it now

```bash
# Kill stale instances
pkill -f 'node server.js' 2>/dev/null || true
sleep 1

# Restart
cd /home/opc/.local/lib/node_modules/@askjo/camofox-browser
nohup npm start > /tmp/camofox.log 2>&1 &

# Wait for browser pre-warm (usually < 2s)
sleep 3
tail -3 /tmp/camofox.log
```
