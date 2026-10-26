---
name: vansrouter-setup
description: |
  VansRouter (github.com/Vanszs/VansRouter) — free AI gateway + router with
  Tailscale Funnel and Cloudflare quick tunnel support. Docker-based deployment,
  host-network mode for Tailscale socket access, CLI token auth for tunnel API.
---

# VansRouter Deployment Guide

## What it replaces

VansRouter replaces 9router as the primary AI gateway. Both listen on port 20128
by default — they cannot share the same port. When installing VansRouter alongside
an existing 9router:
- Stop/disable 9router systemd service, OR
- Reconfigure 9router to a different port (e.g. 20129)

## Docker deployment

### Build the image

```bash
cd /path/to/VansRouter-clone
git clone https://github.com/Vanszs/VansRouter.git
cd VansRouter
cp .env.example .env
# Edit .env: set JWT_SECRET, API_KEY_SECRET, ENABLE_TAILSCALE_TUNNEL=true
docker build -t vansrouter:latest .
```

Build takes ~5-10 minutes on aarch64 (Alpine + Node + Tailscale static binaries + Next.js).

### Start the container

```bash
# Stop any existing service on port 20128 first
sudo systemctl stop 9router.service  # if running
sudo systemctl disable 9router.service  # optional: prevent restart loop

# Run with host network (required for Tailscale host socket access)
# IMPORTANT: set --memory. Without it, the container can exit 137 with
# OOMKilled=false (containerd OOM, not Docker OOM) — the OOMKilled flag
# is unreliable. 512m is enough for VansRouter's Node + SQLite runtime.
docker run -d \
  --name vansrouter \
  --restart unless-stopped \
  --network host \
  --memory 512m \
  -v /var/run/tailscale/tailscaled.sock:/var/run/tailscale/tailscaled.sock \
  --env-file .env \
  -e DATA_DIR=/app/data \
  -e PORT=20128 \
  -e NODE_ENV=production \
  -e ENABLE_TAILSCALE_TUNNEL=true \
  -e TAILSCALE_USE_HOST_SOCKET=true \
  -e TAILSCALE_HOST_SOCKET=/var/run/tailscale/tailscaled.sock \
  vansrouter:latest
```

Key env vars:
- `ENABLE_TAILSCALE_TUNNEL=true` — enables Tailscale tunnel UI
- `TAILSCALE_USE_HOST_SOCKET=true` — uses host's tailscaled.sock instead of spawning own daemon
- `TAILSCALE_HOST_SOCKET=/var/run/tailscale/tailscaled.sock` — path to host socket
- `DATA_DIR=/app/data` — SQLite DB + runtime data inside container

### Verify it's running

```bash
curl -s http://127.0.0.1:20128/ | head -5  # expect JSON welcome
docker ps --filter name=vansrouter  # should show Up
ss -tlnp | grep 20128  # should show LISTEN
```

## Tunnel API authentication

VansRouter's tunnel API (`/api/tunnel/enable`, `/api/tunnel/tailscale-enable`,
`/api/tunnel/status`) requires a CLI token. The token is derived from the container's
machine-id + salt + cli-secret:

```bash
# Inside the container, the token is computed as:
# SHA256(machine-id + "9r-cli-auth" + cli-secret)[:16]

# To get the token from outside the container:
machine_id=$(sudo docker exec vansrouter cat /app/data/machine-id)
cli_secret=$(sudo docker exec vansrouter cat /app/data/auth/cli-secret)
cli_token=$(echo -n "${machine_id}9r-cli-auth${cli_secret}" | sha256sum | cut -c1-16)

# Use it:
curl -s -X POST \
  -H "X-9r-CLI-Token: ${cli_token}" \
  http://127.0.0.1:20128/api/tunnel/enable
```

Note: the VansRouter container image does **not** include `curl` — you cannot
test the tunnel API from inside the container. Compute the token inside
(`docker exec ... cat ...`) but always run the `curl` test from the **host**:

```bash
curl -s -X POST \
  -H "X-9r-CLI-Token: ${cli_token}" \
  http://127.0.0.1:20128/api/tunnel/enable
```

If requests from the host are rejected as "Local only: CLI token required",
run from inside the container using a different HTTP client (the Alpine base
has `wget`, or install `curl` in a dropped-in exec).

## Cloudflare quick tunnel

VansRouter has built-in Cloudflare quick tunnel support (no account needed):

```bash
# Enable via API (requires CLI token)
curl -s -X POST \
  -H "X-9r-CLI-Token: ${cli_token}" \
  http://127.0.0.1:20128/api/tunnel/enable
```

Response includes `tunnelUrl` (trycloudflare.com) and `publicUrl` (abc-tunnel.us).
Quick tunnel URLs change every time cloudflared restarts — that's expected.

Prerequisites:
- Outbound TCP/UDP port 7844 must be open (cloudflared registration)
- If port 7844 is blocked, cloudflared fails with "Fallback: TCP/UDP port 7844 blocked"

## Tailscale Funnel

VansRouter bundles tailscale + tailscaled binaries (aarch64). To enable Funnel:

### Host must have Tailscale running

```bash
# On the host:
tailscale up --accept-routes
tailscale funnel on http://localhost:20128  # enable funnel for port 20128
```

### Container accesses host's tailscaled via mounted socket

The container's `tailscale-enable` API calls the host's tailscaled through the
mounted socket. If `tailscale-enable` returns "Tailscale not connected. Device may
have been removed", check:

1. Host funnel is actually enabled: `tailscale funnel status --json`
2. Host tailscale is logged in: `tailscale status`
3. Funnel capability granted in Tailscale admin console (Settings → Funnel)

### Funnel hostname

Once enabled, VansRouter gets a `*.tail2<tailnet>.ts.net` hostname via Funnel.
Check with `tailscale funnel status --json` on the host.

## Port conflict resolution

When 9router and VansRouter fight for port 20128:

```bash
# Option A: Move 9router to a different port
sudo sed -i 's/--port 20128/--port 20129/' /etc/systemd/system/9router.service
sudo systemctl daemon-reload
sudo systemctl restart 9router.service

# Option B: Stop 9router entirely (VansRouter replaces it)
sudo systemctl stop 9router.service
sudo systemctl disable 9router.service
```

Check which process holds the port:
```bash
ss -tlnp | grep 20128
ps aux | grep 9router
```

## systemd for 9router (if keeping both)

If you keep 9router alongside VansRouter on a different port, the service file
should be headless (no --tray, which causes immediate exit under systemd):

```ini
[Unit]
Description=9router tunneling service
After=network.target

[Service]
Type=simple
User=opc
ExecStart=/usr/bin/node /home/opc/.local/lib/node_modules/9router/cli.js \
  --port 20129 --host 0.0.0.0 --no-browser
Restart=always
RestartSec=5
Environment=NODE_ENV=production
WorkingDirectory=/home/opc
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Note: `--no-browser` prevents browser-open attempts; `--tray` causes immediate
exit under systemd without a GUI session.

## Verification checklist

- [ ] `docker ps` shows vansrouter container Up
- [ ] `curl http://127.0.0.1:20128/` returns 200 with JSON welcome
- [ ] `ss -tlnp | grep 20128` shows LISTEN on 0.0.0.0:20128
- [ ] Cloudflare tunnel: `curl https://<tunnel-url>.trycloudflare.com/` returns 200
- [ ] Tailscale Funnel: `tailscale funnel status --json` shows port 20128 handler
- [ ] CLI token works: `curl -H "X-9r-CLI-Token: <token>" http://127.0.0.1:20128/api/tunnel/status` returns JSON
- [ ] No port conflict: only ONE process listening on 20128
