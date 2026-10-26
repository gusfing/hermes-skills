---
name: service-exposure-and-autostart
description: Expose a service over Tailscale and wire OS autostart.
tags: [tailscale, systemd, auth, autostart]
related_skills: [tailnet-service-exposure]
---

# Service exposure + autostart

Class of task: “run app X on this box, reach it from my iPhone over Tailscale,
require a password, and survive reboots.”

## Step 0 — Reconcile the brief with the machine BEFORE acting

User briefs are frequently wrong: wrong runtime, already-cloned repo,
already-installed deps, already-running server, existing Tailscale Serve config,
dormant systemd unit. Run one reconnaissance pass and report mismatches first.

Check:
```bash
cd <repo> && git remote -v && ls
cat /etc/os-release | head -5
which node npm python3 tailscale
tailscale status; tailscale ip -4
tailscale serve status
ss -lntp | grep <port>
systemctl --user list-unit-files | grep -i <name>
```

Do not perform a step whose precondition is already satisfied. State the
corrections plainly — they are usually the most valuable part of the reply.

## Step 1 — Discover the app’s lifecycle before starting it

Many apps ship a controller (`ctl.sh`, `pm2`, `supervisord`, Docker compose,
`launchd` plist). Prefer it over `nohup`, `&`, or ad-hoc `bootstrap.py`
invocations. Benefits: PID file, single stop path, log file, health-aware
restart.

Audit the repo root and docs first:
```bash
ls -la <repo>
grep -RniE 'ctl\.sh|start\.sh|pm2|supervisord|systemd|launchd' <repo> | head -50
```

## Step 2 — Auth BEFORE reachability

Never widen network exposure before confirming the auth gate is live. Order:
set the password, restart, prove auth works, then open the network path.

Generate the secret with a CSPRNG:
```bash
python3 -c "import secrets,string; a=string.ascii_letters+string.digits; print(''.join(secrets.choice(a) for _ in range(24)))"
```

Do not place credentials in a repo `.env`; use a systemd `EnvironmentFile` with
mode `600`, a secrets manager, or an OS key store appropriate to the host.

Confirm auth with real endpoints from the app’s source rather than guessing
form routes. For `hermes-webui`, verify both directions and cookie persistence:

```bash
curl -s -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -d '{"password":"<real>"}' $URL/api/auth/login    # expect 200
curl -s -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -d '{"password":"nope"}'   $URL/api/auth/login    # expect 401
curl -s -o /dev/null -w '%{http_code}' $URL/api/sessions   # expect 401
curl -s -o /tmp/auth_session.txt -c /tmp/session_cookie.txt \
  -X POST -H 'Content-Type: application/json' \
  -d '{"password":"<real>"}' $URL/api/auth/login       # expect 200
curl -s -b /tmp/session_cookie.txt -o /dev/null -w '%{http_code}' $URL/api/sessions  # expect 200
```

If the first request returns 200 but the second still returns 401, the client
is not storing cookies. That is the signature of Mobile Safari Private
Browsing or strict cookie blocking. Do not widen exposure further; fix the
client/cookie path first.

If you cannot get a definitive 401 without credentials, treat auth as NOT
proven and do not expand exposure. Fail closed.

## Step 3 — Orphan-sweep before enabling a new unit

Before enabling systemd for a port-bound service, audit existing listeners:
```bash
ss -tlnp | grep <port>
lsof -iTCP:<port> -sTCP:LISTEN
```

Kill orphans by PID before enabling the new unit. Otherwise the unit fails to
bind while `/health` still answers 200 from the old process — looks like success
but is not the unit you just enabled.

After start, confirm the listening PID belongs to the unit's cgroup:
```bash
ps -o pid,user,cmd -p $(ss -tlnp | awk '/:<port> /{print $NF}' | sed 's/.*pid=//;s/.*)//')
```

## Step 3b — Audit for services running with NO supervision

“Make X always working” usually means a service that is *running but undefended*.
A long-lived process on a `pts/N` tty, or whose parent is a shell rather than an
init, dies with that shell. Audit before writing any config:

```bash
# parent PID 1 = supervised by init/systemd; a shell or tty parent = not
ps -o pid,ppid,tty,stat,etime,args -C node | grep -v grep
ps -o pid,ppid,args -p <pid>            # walk the parent chain
ls ~/.config/systemd/user/ | grep -i <name>   # a unit already exists?
crontab -l 2>&1; grep -rl <name> /etc/rc.d/rc.local ~/.bashrc ~/.profile 2>/dev/null
```

Two things this catches that “is it up?” never will:

- **The sibling-tool pattern.** A related tool is *already* supervised while this one
  is not. Read the working unit and copy it verbatim — matching paths, flags, log
  destination, and `WantedBy` — rather than authoring from scratch. Consistency beats
  a fresh hand-rolled unit, and it is faster to review.
- **A unit file that exists but is not enabled.** A disabled unit, or one whose
  `default.target.wants` symlink is missing, is a service that comes back after
  *you* restart it and not after a reboot.

Note the flip side of a supervised service: `NRestarts` climbing means a real crash
loop. One increment from your own `kill -9` test is expected — record it rather than
reporting it as a failure.

`loginctl show-user <user> --property=Linger` must be `yes` for user units to survive
logout and reboot on a headless box; otherwise `enable` is silently insufficient.

## Step 4 — Reachability: Serve first, bind second, then validate cookies

Preferred: `tailscale serve` gives HTTPS with a real cert and a stable hostname
— no TLS warnings on iOS Safari.
```bash
tailscale serve --bg <port>
tailscale serve status   # -> https://<host>.<tailnet>.ts.net proxy 127.0.0.1:<port>
```

Only if Serve is disabled on the tailnet, fall back to binding `0.0.0.0` on the
service, and only after Step 2 passed. Give the user the HTTPS hostname, not the
100.x IP; the IP works but produces cert warnings.

### 4a — Mobile/webview auth cookie validation

When the client is an iPhone app or webview, cookie persistence is the usual
silent failure. After confirming `/api/sessions` returns `401` without creds,
run a login + session probe to prove the cookie survives across requests:

```bash
curl -s -o /tmp/login_body.txt -w '%{http_code}' \
  -X POST -H 'Content-Type: application/json' \
  -c /tmp/session_cookie.txt \
  -d '{"password":"<real>"}' $URL/api/auth/login   # expect 200
curl -s -b /tmp/session_cookie.txt -o /dev/null -w '%{http_code}' \
  $URL/api/sessions                                  # expect 200
```

If the first returns `200` but the second still returns `401`, the client is
blocking or dropping cookies. Common causes:
- iOS Private Browsing
- Hermex/webview blocking third-party cookies on `*.ts.net`
- App-specific TLS/cert handling

Do not widen exposure to “fix” this; change the client path first.

### 4b — Tailscale Serve hostname limitation

`tailscale serve` maps only one root handler per hostname on `:443`. You cannot
simultaneously serve `/` → one backend and `/dashboard` → another on the same
`<host>.ts.net` hostname via Serve. If you need multiple apps over Tailscale:
- use distinct Tailscale Serve hostnames, or
- bind each app to `0.0.0.0:<port>` and access via `http://<tailscale-ip>:<port>`.

OmniRoute Dashboard on a different port is a known case that needs the
`0.0.0.0` fallback, not a second Serve route.

### 4c — App-specific outbound ports

Some apps require outbound connectivity on specific ports for tunnel/cloud
features. Example: 9router needs outbound **7844 TCP/UDP** for its
Cloudflare tunnel backend. Open those on the host firewall even if the
service itself binds a different local port.

```bash
sudo firewall-cmd --add-port=7844/tcp --permanent
sudo firewall-cmd --add-port=7844/udp --permanent
sudo firewall-cmd --reload
```

**Crucial: do NOT test outbound 7844 with `timeout 5 bash -c 'echo > /dev/tcp/1.1.1.1/7844'`.**
That probes 1.1.1.1 (a DNS resolver), not Cloudflare's tunnel backend — it gives a false negative.
To actually test tunnel capability, either:
- Run `cloudflared tunnel --url http://localhost:<port>` and watch for a trycloudflare URL in the log (the real test), or
- Check `sudo firewall-cmd --list-all` for `7844/tcp` and `7844/udp` in the `ports:` list.

For VansRouter specifically, when outbound 7844 is blocked the in-container
cloudflared cannot register and the container restarts. The host-side bypass
(run a separate host `cloudflared tunnel --url http://localhost:20128`) often
still works — see `references/vansrouter-7844-blocked.md`.

## Step 5 — Autostart as a human user

Build a systemd user unit with:
```ini
After=network-online.target tailscaled.service
Wants=network-online.target
```

Use the app controller in `ExecStart`, never raw `bootstrap.py` from a shell
wrapper. Then verify:
```bash
systemctl --user is-enabled <svc>   # enabled, not just running
systemctl --user status <svc>
```

Never let the unit run as root by default. A root-run service silently writes
root-owned files into the user's state dir, breaking later non-root runs. Check
ownership after setup:
```bash
find <state-dir> -user root | head
```

### systemd pitfall — Hermes-managed node binary

When the service's `ExecStart` points at a Hermes-managed node binary
(`~/.hermes/node/bin/node` via `~/.local/bin/node` symlink), systemd may
return `203/EXEC` ("Permission denied") even when the binary is world-executable.
Root cause is the Hermes venv's node living under `~/.hermes/` — systemd's
private namespace for `User=opc` may not traverse the hermetic Hermes install
tree the same way an interactive shell does.

**Fix:** use the system node directly:

```ini
ExecStart=/usr/bin/node /path/to/cli.js ...
```

Verify the system node exists and is executable:
```bash
ls -la /usr/bin/node   # must be -rwxr-xr-x (or better)
/usr/bin/node --version
```

If no system node is available, provision one with `apt install nodejs` / `dnf
install nodejs` rather than relying on the Hermes-managed symlink.

### Cloudflare quick tunnel fails silently when outbound 7844 is blocked

VansRouter's dashboard `/api/tunnel/enable` spawns an **in-container** cloudflared process.
If outbound TCP/UDP 7844 is blocked on the host, that process cannot register and is SIGKILLed.
The failure surface looks like this:

- `curl -X POST .../api/tunnel/enable` returns empty body or exit 52/56
- Container exits 137, `docker inspect ... OOMKilled` returns `false`
- `docker stats` shows `0B / 0B` (container already dead when stats polled)
- No `/tmp/vans-tunnel/creds.json` or equivalent is produced — quick tunnel never got a URL
- Container enters a restart loop: Start → Ready → tunnel API called → cloudflared spawns → 7844 blocked → killed → restart

Diagnose before retrying:

```bash
# Confirm 7844 is blocked outbound from this host
timeout 5 bash -c 'echo > /dev/tcp/1.1.1.1/7844' 2>&1 \
  && echo "7844 OUTBOUND OPEN" \
  || echo "7844 OUTBOUND BLOCKED"

# Check for existing host cloudflared processes (9remote or others)
ps aux | grep cloudflared | grep -v grep

# Check port 7844 is NOT already bound by another cloudflared
ss -tlnp | grep 7844
```

**Working bypass: run the Cloudflare tunnel from the HOST, not the container.**

Skip `ENABLE_TAILSCALE_TUNNEL` for VansRouter entirely when 7844 is blocked.
Start VansRouter as a plain API gateway (no tunnel env vars), then run a separate
host `cloudflared tunnel --url http://localhost:20128` process.

```bash
# 1. Start VansRouter WITHOUT tunnel env (plain gateway, stable ~75MB)
sudo docker run -d \
  --name vansrouter \
  --restart unless-stopped \
  --network host \
  --env JWT_SECRET=... \
  --env API_KEY_SECRET=... \
  --env INITIAL_PASSWORD=... \
  --env DATA_DIR=/app/data \
  --env PORT=20128 \
  --env NODE_ENV=production \
  -v /var/run/tailscale/tailscaled.sock:/var/run/tailscale/tailscaled.sock \
  vansrouter:latest

# 2. Verify it's live before touching tunnels
curl -s http://127.0.0.1:20128/   # expect JSON welcome
sudo docker stats vansrouter --no-stream   # confirm not restarting

# 3. Run host cloudflared tunnel (separate from container)
mkdir -p /tmp/vans-tunnel
cat > /tmp/vans-tunnel/config.yml << 'EOF'
tunnel: vansrouter-20128
credentials-file: /tmp/vans-tunnel/creds.json
protocol: http2
ingress:
  - service: http://localhost:20128
EOF

cloudflared tunnel --url http://localhost:20128 \
  --config /tmp/vans-tunnel/config.yml \
  --no-autoupdate --protocol http2 &

# 4. Wait for creds.json (cloudflared prints the trycloudflare URL to stdout)
sleep 15
cat /tmp/vans-tunnel/creds.json   # should exist now
ps aux | grep cloudflared | grep 20128 | grep -v grep   # should be running
```

The real test for 7844 is to run `cloudflared tunnel --url http://localhost:20128` and watch for a trycloudflare.com URL in the log within 15s. If you get a URL, the tunnel works — regardless of what a `timeout 5 bash -c 'echo > /dev/tcp/1.1.1.1/7844'` probe said (that probes 1.1.1.1, a DNS resolver, not Cloudflare's tunnel backend). Check `sudo firewall-cmd --list-all` for `7844/tcp` and `7844/udp` in the `ports:` list as a secondary indicator. If host cloudflared genuinely fails (no URL after 30s, connectivity pre-checks fail in the log), THEN fall back to Tailscale Funnel.

**If 7844 IS open**, you can instead use the VansRouter dashboard API directly:

```bash
machine_id=$(sudo docker exec vansrouter cat /app/data/machine-id)
cli_secret=$(sudo docker exec vansrouter cat /app/data/auth/cli-secret)
cli_token=$(echo -n "${machine_id}9r-cli-auth${cli_secret}" | sha256sum | cut -c1-16)
curl -s -X POST -H "X-9r-CLI-Token: ${cli_token}" \
  -H "Content-Length: 0" \
  http://127.0.0.1:20128/api/tunnel/enable
# response includes tunnelUrl (trycloudflare.com) and publicUrl
```

Note: the container image has no `curl`, so API calls must go through the host's
curl or via `docker exec ... node -e '...'` using Node's `http` module. However, when the container runs with `--network host` and `ENABLE_TAILSCALE_TUNNEL=true`, calling the tunnel API from the **host** via `curl` may return exit 52/56 or "Local only" because the in-container cloudflared is already occupying port 20128 or crashing — use the host-side tunnel approach below instead.

### Host-side Cloudflare tunnel (no container involvement)

When VansRouter's in-container cloudflared is unreliable (restart loops, 7844 blocked, SIGKILL), run the Cloudflare tunnel **entirely from the host** — a separate `cloudflared` process proxying to localhost:20128. This bypasses the container's cloudflared entirely.

```bash
# 1. Start VansRouter as a plain gateway (no ENABLE_TAILSCALE_TUNNEL)
sudo docker run -d \
  --name vansrouter \
  --restart unless-stopped \
  --network host \
  --env JWT_SECRET=... \
  --env API_KEY_SECRET=... \
  --env INITIAL_PASSWORD=... \
  --env DATA_DIR=/app/data \
  --env PORT=20128 \
  --env NODE_ENV=production \
  -v /var/run/tailscale/tailscaled.sock:/var/run/tailscale/tailscaled.sock \
  vansrouter:latest

# 2. Verify it's live
curl -s http://127.0.0.1:20128/   # expect JSON welcome

# 3. Run host cloudflared tunnel (no config file needed for quick tunnel)
nohup /usr/local/bin/cloudflared tunnel \
  --url http://localhost:20128 \
  --no-autoupdate --protocol http2 \
  > /tmp/cloudflared-20128.log 2>&1 &

# 4. Wait for URL (printed to log within ~10-15s)
sleep 12
grep trycloudflare /tmp/cloudflared-20128.log
curl -s https://<tunnel-url>.trycloudflare.com/  # expect 200 + JSON welcome
```

**Crucial test for 7844: do NOT test against 1.1.1.1.** The quick tunnel registers via Cloudflare's argotunnel endpoints (region1.v2.argotunnel.com), not 1.1.1.1. The test `timeout 5 bash -c 'echo > /dev/tcp/1.1.1.1/7844'` is a bad probe — it checks arbitrary connectivity to a DNS resolver on a non-tunnel port, not whether cloudflared can reach its tunnel backend. To actually test outbound tunnel capability, either:
- Run `cloudflared tunnel --url ...` and watch for the URL in the log (the real test), or
- Check the host firewall's port list for 7844/tcp + 7844/udp: `sudo firewall-cmd --list-all` — if both appear in `ports:`, outbound is open.

**If the host cloudflared gets a URL**, the tunnel is working — you do NOT need 7844 open for the `--url` quick tunnel mode in the way previously documented. The earlier "7844 blocked → no URL" conclusion was based on a faulty 1.1.1.1 probe. Re-test with an actual cloudflared run before falling back to Tailscale Funnel.

**If host cloudflared genuinely fails** (no URL after 30s, connectivity pre-checks fail), then fall back to Tailscale Funnel.

### Tailscale Funnel as the alternative when Cloudflare is blocked

When outbound 7844 is blocked and Cloudflare quick tunnel cannot work, Tailscale
Funnel is the reliable path because it uses the existing Tailscale mesh, not a new
outbound port.

```bash
# Host must have Tailscale running and Funnel capability granted
tailscale status                      # confirm logged in
tailscale funnel status --json        # see current funnel handlers

# Enable Funnel for VansRouter's port
tailscale funnel on http://localhost:20128

# Verify
tailscale funnel status --json        # should show port 20128 handler
```

VansRouter gets a `*.tail2<tailnet>.ts.net` hostname. Check the exact hostname
from `tailscale funnel status --json` — it is NOT the same as the 443 Funnel
hostname (only one root handler per hostname on `:443`, see 4b above).

---

### OOMKilled=false trap (validated)

When a Docker container exits 137 but `docker inspect ... --format '{{.State.OOMKilled}}'` returns `false`, do **not** trust that flag. The container may still be OOM-killed by the containerd/cgroup layer (not Docker's own OOM detector). Before assuming a different cause:

1. Check host `dmesg | grep -i oom`
2. Check `sudo docker stats` for the dead container's peak memory
3. Check `free -m` on the host

The fix is often simply `--memory 512m` (or appropriate value) on the `docker run` — VansRouter is a Node + SQLite runtime that needs ~75MB steady-state but can spike without a ceiling.

VansRouter (github.com/Vanszs/VansRouter) is the current-generation AI gateway
that replaces 9router. Key differences:

- **Docker-based** — runs in a Docker container, not a native Node systemd service
- **Host network mode** — requires `--network host` for Tailscale host socket access
- **Built-in tunnels** — Cloudflare quick tunnel + Tailscale Funnel via dashboard API
- **CLI token auth** — tunnel API uses machine-id + salt + cli-secret SHA256 hash

See `references/oracle-linux-cockpit-selinux.md` for SELinux + Cockpit auth failures on Oracle Linux (pam_sepermit.so, cockpit_ws_t context, /etc/shadow access). See `references/vansrouter-setup.md` for full deployment guide and `references/vansrouter-7844-blocked.md` for the 7844-blocked failure mode and host-side bypass.

See `references/ai-gateway-supervision.md` for supervising a local AI gateway on
port 20128: the self-referential case (it serves the agent's own model provider),
copying a sibling's working unit, and why only a real authenticated inference call
counts as verification.

### 9router → VansRouter migration

When migrating from 9router to VansRouter:

1. Stop 9router: `sudo systemctl stop 9router.service`
2. Build VansRouter Docker image (see reference)
3. Start VansRouter on port 20128 (same port, replaces 9router)
4. Enable tunnels via API with CLI token

If keeping both, move 9router to a different port (e.g. 20129) to avoid conflict.

### Tunnel API auth (VansRouter-specific)

VansRouter's tunnel API endpoints require a CLI token header:

```bash
# Compute token from container files
machine_id=$(sudo docker exec vansrouter cat /app/data/machine-id)
cli_secret=$(sudo docker exec vansrouter cat /app/data/auth/cli-secret)
cli_token=$(echo -n "${machine_id}9r-cli-auth${cli_secret}" | sha256sum | cut -c1-16)

# Use:
curl -H "X-9r-CLI-Token: ${cli_token}" http://127.0.0.1:20128/api/tunnel/status
```

Requests from the host may be rejected as "Local only" — run from inside the
container or ensure the source IP is seen as loopback by the dashboardGuard.

### Tailscale Funnel via host socket

VansRouter's container accesses the host's tailscaled through a mounted Unix socket:

```bash
 docker run ... \
  --network host \
  -v /var/run/tailscale/tailscaled.sock:/var/run/tailscale/tailscaled.sock \
  -e TAILSCALE_USE_HOST_SOCKET=true \
  -e TAILSCALE_HOST_SOCKET=/var/run/tailscale/tailscaled.sock \
  vansrouter:latest
```

The host must have Tailscale running and Funnel enabled for the target port:
```bash
tailscale funnel on http://localhost:20128
```

Common failure: `tailscale-enable` API returns "Device may have been removed" —
check host funnel status and Tailscale admin console Funnel settings.

## Verification

SSH tunnel command for a service on port P1 (Hermes) and P2 (9router):
```bash
ssh -L P1:127.0.0.1:P1 -L P2:127.0.0.1:P2 -i <key> -p 22 opc@<host>
```

For background (disconnects from SSH session don't kill the tunnel):
```bash
ssh -f -N -L P1:127.0.0.1:P1 -L P2:127.0.0.1:P2 -i <key> -p 22 opc@<host>
```

Verify both ports are listening after tunnel is up:
```bash
ss -tlnp | grep -E 'P1|P2'
```

Always confirm the service is actually listening *before* relying on the tunnel:
```bash
curl -s --max-time 3 http://127.0.0.1:<port> | head -5
```
