# 9router systemd service setup

## Verified working configuration (2026-09-02)

9router (v0.5.45) runs as a systemd service on Oracle Linux 9 ARM64, listening on `127.0.0.1:20128`.

### Service file

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

### Install

```bash
sudo systemctl daemon-reload
sudo systemctl enable 9router
sudo systemctl restart 9router
```

### Verify

```bash
sudo systemctl status 9router --no-pager -l
ss -tlnp | grep 20128
curl -s --max-time 3 http://127.0.0.1:20128   # expect /dashboard
```

Healthy state: `active (running)`, port 20128 LISTEN, HTTP responds with dashboard HTML.

## Pitfalls

- **Must use `/usr/bin/node`, NOT `~/.hermes/node/bin/node`.** The Hermes-installed Node.js binary lacks the execute bit for systemd's exec context, producing `203/EXEC` ("Failed to locate executable ... Permission denied") even though `ls -la` shows `-rwxr-xr-x`. The system Node at `/usr/bin/node` (v20.20.2) works reliably.
- **`--tray` flag is required** for long-running service mode. Without it, 9router exits after startup (clean exit, status=0/SUCCESS) and systemd restarts it in a loop. With `--tray`, the process stays alive.
- **DB driver warning is transient.** On startup 9router may log "[DB] No SQLite driver available (bun/better/node/sql.js all failed)" while it probes for drivers. This is a FUSE-style probe, not a real failure — the service continues and the SQLite DB (`~/.9router/db/data.sqlite`) works fine. Don't treat this log line as a service failure.
- **Memory:** ~50-120MB RSS typical, peak ~137MB. On a 10GB VPS this is negligible.
- **First-run npm installs.** On first `systemctl start`, 9router may run `npm install` for native deps (`systray2`, `better-sqlite3`) inside the service process. This adds ~5s to startup. Subsequent starts are fast.

## SSH tunnel (from Windows)

```powershell
# Interactive (keeps window open)
ssh -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Users\ks209\Downloads\ssh-key-2026-08-01 (2).key" -p 22 opc@137.23.36.156

# Background (no window, persists until you kill it)
ssh -f -N -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Users\ks209\Downloads\ssh-key-2026-08-01 (2).key" -p 22 opc@137.23.36.156
```

- `http://localhost:9120` → Hermes dashboard
- `http://localhost:20128` → 9router dashboard

### Port map

| Local port | Server target | Service |
|---|---|---|
| 9120 | 127.0.0.1:9120 | Hermes dashboard/gateway |
| 20128 | 127.0.0.1:20128 | 9router |

## Start/stop/restart

```bash
sudo systemctl restart 9router   # restart
sudo systemctl stop 9router       # stop
sudo systemctl start 9router      # start (if stopped)
sudo journalctl -u 9router.service --no-pager -n 30   # recent logs
```

9router auto-starts on boot (enabled).