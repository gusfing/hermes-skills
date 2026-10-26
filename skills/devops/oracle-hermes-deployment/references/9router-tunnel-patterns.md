# 9router Tunnel Patterns — Reference

## Overview

9router listens on port 20128 internally. To expose it externally, use Cloudflare tunnels or other reverse proxy solutions.

## Quick Tunnel (Temporary, Testing)

```bash
cloudflared tunnel --url http://localhost:20128
```

**Result:** `https://<random-subdomain>.trycloudflare.com`

**Characteristics:**
- Changes on every restart
- No uptime guarantee
- Good for: testing, one-off sharing, development
- **NOT for:** bookmarks, production use, persistent URLs

## Named Tunnel (Production)

For a persistent, own-domain URL:

```bash
cloudflared tunnel login
cloudflared tunnel create 9router
cloudflared tunnel route dns 9router 9router.kawaki.co.in
cloudflared tunnel run 9router
```

**Result:** `https://9router.kawaki.co.in`

## Notes

- 9Router listens on port 20128 internally
- Never expose the raw port 20128 directly to the internet
- Always use Cloudflare proxy (orange cloud) or a reverse proxy (nginx) for HTTPS termination

## Example Output

When a quick tunnel is created, cloudflared outputs:

```
INF |  Your quick Tunnel has been created! Visit it at:  |
INF |  https://scoop-investigators-freeze-everywhere.trycloudflare.com  |
```

Extract the URL from this output - do not guess the subdomain.

## Verification

```bash
# Check health endpoint
curl -s --max-time 3 http://127.0.0.1:20128/api/health
# Expected: {"ok":true}

# Check tunnel status (if using named tunnel with CLI token)
CLI_TOKEN=$(echo -n "$(cat ~/.9router/machine-id)9r-cli-auth$(cat ~/.9router/auth/cli-secret)" | sha256sum | cut -c1-16)
curl -s -H "x-9r-cli-token: $CLI_TOKEN" http://127.0.0.1:20128/api/tunnel/status
```

## Port Map for SSH Tunnels (Windows)

```powershell
# Interactive (keeps window open)
ssh -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Users\ks209\Downloads\ssh-key-2026-08-01 (2).key" -p 22 opc@137.23.36.156

# Background (no window, persists until you kill it)
ssh -f -N -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Users\ks209\Downloads\ssh-key-2026-08-01 (2).key" -p 22 opc@137.23.36.156
```

- `http://localhost:9120` → Hermes dashboard
- `http://localhost:20128` → 9router dashboard

## Important: Tunnel vs Direct Access

Both `cloudflare-service-exposure` paths terminate at the same app port (20128):

```
A record + nginx    browser → nginx:80 → app:20128
cloudflared tunnel  browser → CF edge → app:20128
```

**Critical pitfall:** Auth added to nginx only protects the A record path. A tunnel reaches the app directly, bypassing nginx entirely. Always enforce auth at the application layer when multiple access paths exist.