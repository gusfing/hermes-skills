# 9router — operational lifecycle and failure signatures

## Systemd service (verified 2026-09-02)

`/etc/systemd/system/9router.service`:

```ini
[Unit]
Description=9router tunneling service
After=network.target

[Service]
Type=simple
User=opc
ExecStart=/usr/bin/node /home/opc/.local/lib/node_modules/9router/cli.js --port 20128 --host 127.0.0.1 --tray
Restart=always
RestartSec=5
Environment=NODE_ENV=production
WorkingDirectory=/home/opc
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Install:

```bash
sudo systemctl daemon-reload
sudo systemctl enable 9router
sudo systemctl restart 9router
```

## Node binary — MUST use `/usr/bin/node`

9router's systemd service MUST use `/usr/bin/node` (system Node v20.20.2), NOT `~/.hermes/node/bin/node`.

- `~/.hermes/node/bin/node` is a Ceres-sandboxed venv binary. systemd's exec context strips the sandbox env, producing `203/EXEC` ("Failed to locate executable ... Permission denied") even when `ls -la` shows `-rwxr-xr-x`.
- `/usr/bin/node` v20.20.2 is the system binary — works reliably under systemd.
- If the service file says `ExecStart=/home/opc/.local/bin/node ...`, change it to `/usr/bin/node`.

## `--tray` flag is REQUIRED for systemd

Without `--tray`, 9router exits immediately after printing startup banner (clean exit, `status=0/SUCCESS`), and systemd restarts it in an infinite loop.

With `--tray`, the process stays alive as a background service.

```bash
# WRONG — exits immediately, systemd loop
ExecStart=/usr/bin/node .../cli.js --port 20128 --host 127.0.0.1

# CORRECT — stays alive
ExecStart=/usr/bin/node .../cli.js --port 20128 --host 127.0.0.1 --tray
```

## DB driver resolution

9router has 4 SQLite adapters (in priority order): bun:sqlite → better-sqlite3 → node:sqlite (Node ≥22.5) → sql.js.

The startup probe logs **"[DB] No SQLite driver available (bun/better/node/sql.js all failed)"** when it checks each adapter and the first 3 don't resolve. **This is transient, not a failure** — the probe continues to sql.js (bundled), and the service starts normally.

If the error persists across restarts AND the service stays down, better-sqlite3 is genuinely missing from the app's module resolution path.

### Fixing a real missing-driver failure

If 9router restarts continuously AND `journalctl` shows the DB error as the last log line before exit, install better-sqlite3 into the app's node_modules:

```bash
cd /home/opc/.local/lib/node_modules/9router/app
npm install better-sqlite3@13.0.3
```

This resolves the module because 9router's compiled server code loads `better-sqlite3` relative to the app package root, not the runtime dir. Verify:

```bash
cd /home/opc/.local/lib/node_modules/9router/app
node -e "const b = require('better-sqlite3'); console.log('OK:', typeof b);"
```

### ABI mismatch — the real cause of persistent "[DB] No SQLite driver available"

The more common failure mode: better-sqlite3's `.node` binary was compiled for a **different Node.js ABI** than the one 9router's server uses.

**Symptom:** `better-sqlite3` loads fine from the command line but 9router's server still reports "No SQLite driver available". Or: `npm rebuild` succeeds but loading still fails with `NODE_MODULE_VERSION` mismatch.

**Root cause:** 9router's runtime dir (`~/.9router/runtime/node_modules/better-sqlite3`) contains a `.node` compiled for Node v22 (ABI 127), but the systemd service uses `/usr/bin/node` v20 (ABI 115). The `npm rebuild` earlier in this session deleted the old `.node` but the rebuild also targeted Node 22 (because npm's default `node` resolved to Hermes's Node 22, not system Node 20).

**Diagnostic:**

```bash
# Check which Node the running 9router uses
cat /proc/$(pgrep -f "9router/cli.js" | head -1)/environ | tr '\0' '\n' | grep PATH

# Check the .node ABI version
node -e "
const fs = require('fs');
const buf = fs.readFileSync('/home/opc/.9router/runtime/node_modules/better-sqlite3/build/Release/better_sqlite3.node');
// NODE_MODULE_VERSION is at offset 8 in the magic header
const abi = buf.readUInt16LE(8);
console.log('ABI version:', abi, '(115=Node20, 127=Node22)');
"

# Check Node version used by npm/node-gyp
which node && node --version  # If this is v22, rebuilds target ABI 127
```

**Fix — rebuild for Node 20 (system node):**

```bash
# 1. Use system node-gyp, not npm's node-gyp (which may use wrong Node)
cd /home/opc/.9router/runtime/node_modules/better-sqlite3

# 2. Rebuild with system node explicitly
bash /usr/lib/node_modules/npm/bin/node-gyp-bin/node-gyp \
  rebuild --release \
  --target=20.20.2 \
  --arch=arm64 \
  --dist-url=https://nodejs.org/dist

# 3. Verify the .node was rebuilt for ABI 115
node -e "
const fs = require('fs');
const buf = fs.readFileSync('build/Release/better_sqlite3.node');
console.log('ABI version:', buf.readUInt16LE(8), '(expect 115)');
"

# 4. Symlink into app's node_modules (Next.js standalone mode)
mkdir -p /home/opc/.local/lib/node_modules/9router/app/node_modules
ln -sf /home/opc/.9router/runtime/node_modules/better-sqlite3 \
  /home/opc/.local/lib/node_modules/9router/app/node_modules/better-sqlite3

# 5. Restart 9router
sudo systemctl restart 9router
```

**Why the symlink is needed:** 9router ships as a Next.js standalone build. The compiled server code (`.next-cli-build/server/...`) requires `better-sqlite3` via webpack module IDs, but Next.js standalone mode resolves native modules from the app's own `node_modules` (not from `NODE_PATH`). The runtime dir's `better-sqlite3` is invisible to Next.js unless symlinked into the app's `node_modules`.

**Verification after fix:**

```bash
# Wait for 9router to start, then test with CLI token
CLI_TOKEN=$(echo -n "$(cat ~/.9router/machine-id)9r-cli-auth$(cat ~/.9router/auth/cli-secret)" | sha256sum | cut -c1-16)
curl -s -H "x-9r-cli-token: $CLI_TOKEN" http://127.0.0.1:20128/api/tunnel/status
# Expected: {"tunnel":{"enabled":false,...},"tailscale":{...},...} — NOT an error
```

If the response still contains `"error":"[DB] No SQLite driver available"`, the symlink didn't take or the wrong `.node` is being loaded. Check that the symlink target is the rebuilt (ABI 115) version.

### The node-gyp invocation trap

Calling `node-gyp` directly via `/usr/bin/node node-gyp` or `npx node-gyp` may use the wrong Node.js version for the rebuild. In this environment, `npx node-gyp` resolves to Hermes's Node 22 (via `~/.hermes/node`), not system Node 20.

**Always use the bash wrapper directly:**
```bash
bash /usr/lib/node_modules/npm/bin/node-gyp-bin/node-gyp rebuild --release ...
```

This bash script explicitly invokes the system's node-gyp with the correct Node binary.

## Crash-recovery loop diagnosis

Symptom: `ERR_CONNECTION_RESET` / `ERR_EMPTY_RESPONSE` in browser, 9router restarts repeatedly.

Diagnosis steps:

1. Check restart count: `sudo systemctl show 9router --property=NRestarts`
2. Check if it's actually up: `ss -tlnp | grep 20128` and `curl -s --max-time 3 http://127.0.0.1:20128/api/health` (expect `{"ok":true}`)
3. If health check fails with connection refused → process died. Check journal: `sudo journalctl -u 9router.service --no-pager -n 30`
4. If journal is silent (no error lines, just clean exit 0) → process exited via unhandled promise rejection or SIGTERM without logging. Restart and watch.
5. If journal shows DB error as last line → driver issue (see above).
6. If health check succeeds but browser still sees resets → the crash is happening in a Next.js render path (SSR route handlers crash, static assets are fine). The `/api/auth/login` POST handler is a common crash point if the DB adapter fails to initialize.

Healthy state: `active (running)`, port 20128 LISTEN, health endpoint returns 200, no restarts in last 10 minutes.

## Log levels

```bash
# Recent service logs (systemd-managed)
sudo journalctl -u 9router.service --no-pager -n 30

# Follow live
sudo journalctl -u 9router.service -f

# Full output (including process stdout/stderr)
sudo journalctl -u 9router.service --no-pager -o cat -n 50
```

9router writes to stdout (startup banner, server URL) and stderr (errors). systemd captures both.

## Port map

| Local port | Server target | Service |
|---|---|---|
| 9120 | 127.0.0.1:9120 | Hermes dashboard/gateway |
| 20128 | 127.0.0.1:20128 | 9router |

## SSH tunnel (Windows)

```powershell
# Interactive
ssh -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Users\ks209\Downloads\ssh-key-2026-08-01 (2).key" -p 22 opc@137.23.36.156

# Background (no window)
ssh -f -N -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Users\ks209\Downloads\ssh-key-2026-08-01 (2).key" -p 22 opc@137.23.36.156
```

- `http://localhost:9120` → Hermes dashboard
- `http://localhost:20128` → 9router dashboard

## Memory footprint

~50-130MB RSS typical, peak ~190MB during npm install of native deps. Negligible on 10GB VPS.

## First-run npm installs

On first `systemctl start`, 9router may run `npm install` inside the service process for native deps (`systray2`, `better-sqlite3`). Adds ~5s to startup. Subsequent starts are fast.

## Hermes integration

Hermes uses 9router as a custom provider:

```yaml
model:
  default: "free"
  provider: "custom"
  base_url: "http://127.0.0.1:20128/v1"
```

9router does NOT expose `/api/mcp` — do not attempt MCP connections to it.
