## 9router systemd service on Oracle Linux 9 aarch64 — verified setup

### Service file

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

### Critical details

- **`ExecStart` must use `/usr/bin/node` (system Node v20.20.2), NOT the Hermes-managed symlink at `/home/opc/.local/bin/node` → `/home/opc/.hermes/node/bin/node`.** The Hermes symlinked node had `Permission denied` when systemd tried to exec it as user `opc`, producing `status=203/EXEC` in a restart loop. The system Node at `/usr/bin/node` works.
- **`--tray` flag is required.** Without it, 9router does a one-shot startup, exits successfully (`status=0/SUCCESS`), and systemd restarts it in a loop. With `--tray` it stays resident.
- **Port is `20128`** by default. Bind to `127.0.0.1` only — do not bind `0.0.0.0` (9router warns about this).
- **OOM risk on 10GB hosts.** The node binary is ~122MB. Combined with Hermes gateway (~300MB), WebUI, and other services, parallel `node-gyp` builds of better-sqlite3 can trigger the OOM killer. Build native modules before or after heavy service windows, not during.

### Installation steps

```bash
# 1. Create service file
sudo bash -c 'cat > /etc/systemd/system/9router.service' << 'SVCEOF'
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
SVCEOF

# 2. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable 9router
sudo systemctl restart 9router
sleep 8
sudo systemctl status 9router --no-pager -l

# 3. Verify it is actually listening and responding
ss -tlnp | grep 20128
curl -s --max-time 3 http://127.0.0.1:20128
```

### Verifying DB driver is actually working

The `[DB]` log line is a FUSE probe that runs at startup and checks for `bun`, `better-sqlite3`, `node:sqlite`, and `sql.js`. If none are found it falls back to the bundled `sql.js` and continues. The warning line in the journal looks like:

```
[DB] No SQLite driver available (bun/better/node/sql.js all failed)
```

**This warning is often harmless** — the service can still start, listen, and serve the dashboard. The real verification is:

- `sudo systemctl status 9router` → `Active: active (running)`
- `ss -tlnp | grep 20128` → LISTEN
- `curl -s http://127.0.0.1:20128` → `/dashboard` or HTTP 307

If you want to silence the warning, install `better-sqlite3` as a native module so the FUSE probe finds it.

### Silencing the DB warning: install better-sqlite3 native module

9router's compiled server code loads `better-sqlite3` from the **app's own `node_modules/`** (`/home/opc/.local/lib/node_modules/9router/app/node_modules/`), NOT from the runtime dir (`~/.9router/runtime/node_modules/`). The app's `package.json` declares `"better-sqlite3": "^12.6.2"` but the directory does not contain the package — so the DB adapter factory fails to resolve it and falls back through `bun:sqlite` → `node:sqlite` → `sql.js` → failure.

**Fix — install into the app's module tree:**

```bash
cd /home/opc/.local/lib/node_modules/9router/app
npm install better-sqlite3@13.0.3
```

On linux-arm64, the npm package ships a prebuilt `prebuilds/linux-arm64.node` that loads without compilation:

```bash
# Verify the prebuild loads
cd /home/opc/.local/lib/node_modules/9router/app/node_modules/better-sqlite3
node -e "const b = require('better-sqlite3'); console.log(typeof b, b.version)"
```

If compilation is needed (no prebuild for the platform), compile in the package dir:

```bash
cd /home/opc/.local/lib/node_modules/9router/app/node_modules/better-sqlite3
npx node-gyp rebuild
```

Then restart the service:
```bash
sudo systemctl restart 9router
```

**Verification that the native driver is active:** check the journal for `[DB] Driver: better-sqlite3` instead of the fallback warning.

### 9router ports and SSH tunneling from Windows

9router exposes a web dashboard on its configured port (default `20128`). When running under systemd on the server, tunnel it from a Windows machine alongside Hermes' dashboard:

```
ssh -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Path\To\ssh-key.key" -p 22 opc@<server-ip>
```

- `http://localhost:9120` → Hermes dashboard
- `http://localhost:20128` → 9router dashboard

For a background tunnel that doesn't require an interactive session:
```
ssh -f -N -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Path\To\ssh-key.key" -p 22 opc@<server-ip>
```

### Diagnostics

```bash
# Service status
sudo systemctl status 9router --no-pager -l

# Journal (last 20 lines, cat format)
sudo journalctl -u 9router.service --no-pager -n 20 -o cat

# Listeners
ss -tlnp | grep 20128

# HTTP check
curl -sv --max-time 5 http://127.0.0.1:20128/ 2>&1 | grep -E "< HTTP|error"

# Process
ps aux | grep "9router" | grep -v grep
```

### Common failure signatures

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `status=203/EXEC`, `Permission denied` on exec | Using Hermes node symlink as ExecStart | Switch to `/usr/bin/node` |
| `status=0/SUCCESS` restart loop | Missing `--tray` flag, process exits immediately | Add `--tray` to ExecStart |
| `[DB] No SQLite driver available` but service runs fine | FUSE probe noise; sql.js fallback working | Install better-sqlite3 in app node_modules, or ignore if service healthy |
| Service starts then dies, no listener | OOM kill (check `dmesg` / `journalctl`) | Reduce memory pressure, stop other services |
| `curl` connects but returns nothing | Next.js still compiling on first boot after install | Wait 30-60s, check journal for `next-server` startup |
