---
name: cloudflare-service-exposure
description: Expose a local service via Cloudflare subdomain with HTTPS.
---

# Cloudflare Service Exposure

## Decision: Tunnel vs A-record + reverse proxy

| | Tunnel (`cloudflared`) | A record + reverse proxy |
|---|---|---|
| Inbound port on VPS | **None** — outbound tunnel | Port 80/443 (nginx) or 2785 (direct) |
| Oracle NSG/security list | No change needed | Must allow 80/443 (or 2785 if no proxy) |
| HTTPS | Free, managed by CF | nginx + Let's Encrypt, or CF Flexible SSL |
| Setup complexity | Medium (install + auth) | Low–medium (nginx install + config) |
| Best when | You can't/openly don't want to open ports | You already have port access and want quick HTTPS |

## Path A — A record + nginx reverse proxy (what this session did)

### 1. Create the DNS A record via Cloudflare API

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/dns_records" \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"type":"A","name":"<SUB.domain.ZONE>","content":"<VPS_IP>","ttl":1,"proxied":false}'
```

Minimum token scope: `Zone:DNS:Edit` on the target zone only. Never use the Global API key.

### 2. Toggle proxy (orange cloud) on

```bash
curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/dns_records/<RECORD_ID>" \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"proxied":true}'
```

`proxied: true` routes traffic through Cloudflare's edge (orange cloud in the dashboard). Set to `false` for a grey-cloud (DNS-only) record.

### 3. Install + configure nginx on the VPS (Oracle Linux 9)

See `references/nginx-oracle-linux-runbook.md` for the full runbook.

### 4. Open the port in Oracle Cloud

You still need an ingress rule in Oracle Console → Networking → VCN → Security Lists (or NSG):
- If nginx on 80/443: allow TCP 80 and 443 from `0.0.0.0/0` (or your IP).
- If proxying directly to the app on 2785 without nginx: allow TCP 2785.

Cloudflare's proxy does **not** bypass the origin firewall — it terminates at the edge and forwards to your VPS IP on the port you configured. If that port is blocked at the VPC/NSG layer, Cloudflare returns 522/520.

## Path B — Cloudflare Tunnel (no open inbound ports)

When you can't or don't want to open any inbound port:

1. Install `cloudflared` on the VPS.
2. Authenticate once: `cloudflared tunnel login` (opens a browser; alternatively use an API token).
3. Create a tunnel: `cloudflared tunnel create <NAME>`.
4. Route the subdomain: `cloudflared tunnel route dns <TUNNEL_ID> <SUB.domain.ZONE>`.
5. Run as a systemd service or via `docker run` with the tunnel secret.

Tunnels give you HTTPS for free with no NSG changes. Use this when the Oracle security list is locked down or you don't have console access to it.

## Pitfalls

### A tunnel aimed at the app port bypasses your reverse proxy — and its auth

**This is the one that can publish private data.** Both exposure paths in this
skill terminate at the *same* app port, and they are not equivalent:

```
A record + nginx    browser → nginx:80 → [auth_basic HERE] → app:8791
cloudflared tunnel  browser → CF edge → app:8791   ← nginx never involved
```

Auth added to nginx protects **only the first path**. A tunnel pointed at
`http://127.0.0.1:8791` reaches the app directly, so every request that was
supposed to get a 401 gets a **200**. Nothing errors; the service looks perfect.

The failure mode is that the nginx test passes, so the check stops there:

```bash
# PASSES, but proves nothing about the tunnel
curl -o /dev/null -w "%{http_code}\n" -H "Host: sub.domain" http://127.0.0.1/  # 401

# The one that catches it — no credentials, PUBLIC url
curl -s -o /dev/null -w "%{http_code}\n" https://<public-tunnel-url>/healthz     # 200 → LEAK
```

**Rule: auth goes in the application, not only in the proxy.** If more than one
path can reach the service, enforce at the layer all paths share — the app —
and treat proxy auth as defence in depth. Check before the route dispatch, not
inside each handler, so a new endpoint cannot be added unauthenticated by
omission.

```python
def do_GET(self):
    if not authorized(self.headers.get("Authorization")):   # before routing
        self.send_response(401); self.send_header("WWW-Authenticate", 'Basic realm="d"')
        self.end_headers(); return
    path = self.path.split("?")[0]                          # then dispatch
```

When you finish exposing anything non-public, run the three-case matrix from
the **public** URL, not localhost: no credentials → 401, wrong password → 401,
correct → 200. All three, every time.

### htpasswd 640 root:root → nginx 500, not 401

`htpasswd` creates the file owned by `root:root`. With `auth_basic_user_file`
pointing at it, nginx workers run as `nginx` and cannot read it. nginx does not
report a permissions error — it returns **500**, which reads like an app crash
and sends you debugging the wrong layer.

```bash
sudo chown root:nginx /path/.htpasswd && sudo chmod 640 /path/.htpasswd
sudo -u nginx test -r /path/.htpasswd && echo "readable"   # prove it, don't assume
```

`sudo -u nginx test -r` is the one-line check that distinguishes "auth
misconfigured" from "app broken". Use it before reading app logs.

### A stale manual process holds the port and the unit crash-loops

A service that "won't start" with `status=…/failure` and a bind error is often
an old hand-launched copy of the *same* process still holding the port. The
unit restart-loops, the port still answers — from the old code. Anything you
just deployed is silently not running, and requests appear to work.

```bash
pgrep -af "[s]erver_name\.py"          # note the bracket: a plain pattern
                                        # matches this command line itself
sudo -n ss -ltnp | grep :8791          # who actually owns the socket
```

Kill the manual pid, then confirm the unit, not just the port:

```bash
systemctl --user restart <unit>.service
systemctl --user is-active <unit>.service
systemctl --user show <unit>.service -p NRestarts -p ActiveEnterTimestamp
```

A 404 on a route you *just* added is the tell: the responding process predates
the code. `NRestarts: 0` plus a fresh `ActiveEnterTimestamp` is the proof the
unit — not a stray process — is serving.

Always bracket a pgrep pattern (`[s]erver_name\.py`) so it cannot match its own
command line.

### A quick tunnel URL is not a permanent address

`cloudflared tunnel --url …` yields a `*.trycloudflare.com` hostname that
changes on restart and carries no uptime guarantee. It is right for "look at
this now" and wrong for a bookmark. Say so when handing one over, and offer the
named tunnel (persistent, own hostname, survives restarts) as the real fix.

### SSH to a proxied domain fails

Once a domain is orange-cloud proxied, `ssh user@sub.domain.zone` resolves to a Cloudflare edge IP, **not** your VPS IP. The connection either times out or hits a CF proxy that doesn't speak SSH.

**Fix:** SSH to the raw origin IP directly: `ssh user@<VPS_IP>`. Use the IP, not the subdomain, for all direct server access (SSH, RDP, direct API calls) while the record is proxied.

If you need the subdomain to work for SSH too, either grey-cloud it temporarily (`proxied: false`) or add a separate non-proxied A record (e.g. `ssh.sub.domain.zone`) pointing to the same IP.

### VPS authorized_keys must contain the key you're offering

When SSH fails with `Permission denied (publickey)`, the diagnostic is:

1. What key are you offering? `ssh -i ~/.ssh/key -v user@host ...` — look for `Offering public key: ... SHA256:...`.
2. Is that exact public key in the **target's** `~/.ssh/authorized_keys`?

The local `~/.ssh/authorized_keys` (on the machine you're SSHing *from*) is irrelevant. What matters is the *target's* file. If the offered key's public half isn't in the target's `authorized_keys`, the server rejects it regardless of whether your local key files are valid.

**Fix:** append the public key to the target's `~/.ssh/authorized_keys`:
```bash
# On the target (via console or a working key):
echo "ssh-ed25519 AAAA... comment" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### SELinux 502 on Oracle Linux 9

On Oracle Linux 9, SELinux is enforcing by default. When nginx proxies to a non-standard app port (e.g. 2785), the connect() is denied at the SELinux layer and nginx returns **502** even though the backend is healthy and reachable via `curl` directly. The error in `/var/log/nginx/error.log` reads:

```
connect() to 127.0.0.1:2785 failed (13: Permission denied) while connecting to upstream
```

This is a policy denial, not a network or upstream config error. The fix is the SELinux boolean:

```bash
sudo setsebool -P httpd_can_network_connect 1
```

See `references/nginx-oracle-linux-runbook.md` for the full SELinux section, diagnostic checklist, and the `policycoreutils-python-utils` install step if `setsebool` is missing.

Do NOT `setenforce 0` as a fix — use the boolean.

### Cloudflare proxy does not bypass the origin firewall

Setting `proxied: true` routes traffic through Cloudflare's edge, but the edge still reaches your VPS IP on the configured port. If Oracle's NSG/security list blocks that port, you get 522 (connection timeout) or 520 (empty response). The proxy is not a substitute for opening the port at the VPC layer.

### Error 521 — SSL/TLS mode mismatch (common, easy to miss)

When Cloudflare returns **521 (Web server is offline)** but `curl` to the origin IP on port 80 returns a valid response locally, the problem is almost always a **Cloudflare SSL/TLS mode mismatch**.

**Root cause:** Cloudflare's SSL/TLS setting for the zone is `full` or `full(strict)`, which makes Cloudflare's edge send **HTTPS** to your origin. But your nginx only listens on port 80 (HTTP) — no TLS. The HTTPS handshake fails, and Cloudflare returns 521.

**Check your zone's SSL mode:**
```bash
curl -s -H "Authorization: Bearer <API_TOKEN>" \
  "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/settings/ssl" \
  | jq '.result.value'
# "full", "flexible", or "full_strict"
```

**Fix A — Quick (Flexible SSL):**
Set the zone's SSL mode to `flexible`. Cloudflare terminates HTTPS at the edge and forwards plain HTTP to your nginx on port 80. No cert needed on the VPS.
```bash
curl -s -X PATCH \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/settings/ssl" \
  -d '{"value":"flexible"}'
```
**Trade-off:** Traffic between CF edge and your VPS is plaintext. Fine on a private VCN; not ideal over a public untrusted path.

**Fix B — Proper (Full strict + nginx TLS):**
1. Open port 443 in firewalld and Oracle NSG/security list.
2. Get a cert (Let's Encrypt via certbot, or Cloudflare origin CA cert).
3. Add a `listen 443 ssl` server block in nginx for the subdomain.
4. Keep Cloudflare SSL mode at `full` or `full(strict)`.

**Diagnostic tree for 521:**
1. `curl -sI --max-time 5 https://<SUBDOMAIN>/` → 521? Go to step 2.
2. `curl -s -o /dev/null -w "%{http_code}" http://<ORIGIN_IP>:80/` → 200? nginx is up.
3. Check Cloudflare SSL mode (cmd above). If `full` or `full_strict` → mismatch. Switch to `flexible` (Fix A) or add TLS to nginx (Fix B).
4. If step 2 fails → 522: origin port blocked at firewall/NSG layer (open it).

**This is NOT a network/firewall issue** — the origin is reachable. It is an SSL/TLS protocol mismatch between Cloudflare edge and origin.

### Error 521 variant: "Always Use HTTPS" + Flexible SSL redirect loop

A subtler 521 cause: Cloudflare zone has **SSL = Flexible** AND **Always Use HTTPS = On**. Cloudflare's edge tries to redirect HTTP→HTTPS, but the origin doesn't speak TLS, so the connection resets. Cloudflare reports this as 521 (not a redirect loop — the edge never gets a response).

**Check both settings:**
```bash
# SSL mode
curl -s -H "Authorization: Bearer <API_TOKEN>" \
  "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/settings/ssl" | jq '.result.value'

# Always Use HTTPS
curl -s -H "Authorization: Bearer <API_TOKEN>" \
  "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/settings/always_use_https" | jq '.result.value'
```

**Fix:** Either (a) set SSL to `flexible` AND disable Always Use HTTPS, or (b) set SSL to `full` AND add TLS certs to nginx (see Fix B above). The combination Flexible + Always Use HTTPS is self-defeating.

**This session's exact fix:**
```bash
# 1. Disable Always Use HTTPS
curl -s -X PATCH \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/settings/always_use_https" \
  -d '{"value":"off"}'

# 2. Ensure SSL is Flexible (not full)
curl -s -X PATCH \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/settings/ssl" \
  -d '{"value":"flexible"}'
```

After both changes, `curl -I https://<SUBDOMAIN>/` returns 401 (nginx auth) instead of 521 — the origin is reachable over HTTPS from Cloudflare's edge, and nginx handles the auth challenge.

### Post-third-party-deletion DNS cleanup

When a third-party hosting project (Vercel, Netlify, etc.) is deleted, residual DNS records often keep pointing to dead infrastructure — causing 404s, redirect loops, or proxy IP mismatches even when the new A records look correct.

**Symptoms after deletion:**
- Apex returns 404 `DEPLOYMENT_NOT_FOUND` from the third party
- www does a redirect loop (third-party default for unmatched domains)
- Proxied A records still resolve to old third-party proxy IPs after recreation

**Cleanup checklist (do ALL of these — name filters alone miss shadowing records):**

1. **Enumerate every record pointing to the third party or covering the domain:**
   ```bash
   curl -s -H "Authorization: Bearer $CF_TOKEN" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" | python3 -c "
   import sys,json
   d=json.load(sys.stdin)
   for r in d['result']:
       content = r.get('content','').lower()
       name = r['name'].lower()
       if 'vercel' in content or 'netlify' in content:
           print(f'{r[\"type\"]:6} {r[\"name\"]:30} → {r[\"content\"]:45} ID={r[\"id\"]}')
       if name in ('kawaki.co.in', 'www.kawaki.co.in') or name.startswith('*.'):
           print(f'{r[\"type\"]:6} {r[\"name\"]:30} → {r[\"content\"]:45} ID={r[\"id\"]} (check manually)')
   "
   ```
   Pay special attention to: apex CNAME (overrides A records at same name), wildcard A records (`*.domain.com`), and any CNAME at `www`.

2. **Delete by exact ID** (not by name — wildcards and apex CNAMEs shadow name-based lookups):
   ```bash
   curl -s -X DELETE -H "Authorization: Bearer $CF_TOKEN" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID"
   ```

3. **Purge Cloudflare cache:**
   ```bash
   curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
     -d '{"purge_everything":true}'
   ```

4. **Create fresh A records for apex + www with NEW record IDs:**
   ```bash
   curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
     -d '{"type":"A","name":"kawaki.co.in","content":"SERVER_IP","ttl":1,"proxied":true}'
   curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
     -d '{"type":"A","name":"www","content":"SERVER_IP","ttl":1,"proxied":true}'
   ```
   Don't use a CNAME for `www → apex` when both need proxy — the CNAME chain can break at the Cloudflare proxy layer (www resolves to CF IPs but CF's proxy lookup returns stale Vercel IPs).

5. **Verify DNS from multiple resolvers** (8.8.8.8, 1.1.1.1, Cloudflare authoritative NS):
   ```bash
   dig @8.8.8.8 kawaki.co.in A +short
   dig @1.1.1.1 www.kawaki.co.in A +short
   dig @ns1.cloudflare.com www.kawaki.co.in A +short
   ```
   All should return the new CF proxy IPs (104.21.x.x, 172.67.x.x), not the old third-party IPs.
   **Important:** a single resolver or even Cloudflare's authoritative NS may show the correct IPs while public resolvers (8.8.8.8, 1.1.1.1) still return stale cached proxy IPs for several minutes after record creation. Always check at least two public resolvers in addition to the authoritative NS.

6. **If www still points to stale third-party IPs after recreation:** delete the www record and create a fresh one with a new ID (do NOT just toggle `proxied`). Cloudflare proxy IP assignment is asynchronous and tied to the record ID — a fresh ID forces a fresh proxy assignment.
   ```bash
   # Delete existing www record
   curl -s -X DELETE -H "Authorization: Bearer $CF_TOKEN" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$WWW_RECORD_ID"
   # Purge
   curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
     -d '{"purge_everything":true}'
   # Create fresh
   curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
     -d '{"type":"A","name":"www","content":"SERVER_IP","ttl":1,"proxied":true}'
   ```

### CNAME-at-www-with-proxy trap

When `www` is a CNAME to the apex (`kawaki.co.in`) and both are proxied (orange cloud), the CNAME chain resolves through Cloudflare's proxy. If the apex was previously pointed at a third party (Vercel, etc.), Cloudflare's proxy lookup for the CNAME target can return stale third-party IPs even after the apex A record was fixed. **Symptom:** www resolves to 104.21.x.x / 172.67.x.x (CF proxy IPs) but the actual response comes from the third party's IPs (or a redirect loop back to itself).

**Fix:** delete the www CNAME, create www as an A record directly to the origin IP with `proxied: true`. Do NOT use `www → apex CNAME` when the apex was recently migrated from a third party.

### Why recreating the record matters

Cloudflare proxy IP assignment is asynchronous. After deleting and recreating the same record at the same name, public DNS resolvers may still return the old proxy IPs for several minutes. Deleting → purging → creating a fresh record (new ID) is more reliable than toggling `proxied` on/off on the same record.

### CNAME at apex takes precedence over A record

A CNAME at the zone apex (`kawaki.co.in` CNAME → something) shadows any A record at that same name. If a third-party setup left an apex CNAME and you add an A record, the CNAME wins and the A record is invisible to resolvers. Always enumerate and delete apex CNAMEs when cleaning up after a third-party deletion.

### Vercel project deletion leaves redirect behavior

When a Vercel project is deleted, Vercel's edge IP range still responds to requests for domains that were once configured in that project — but returns:
- **307/308 redirect** for `www` → `www` (redirect loop, ERR_TOO_MANY_REDIRECTS)
- **404 DEPLOYMENT_NOT_FOUND** for the apex

This persists as long as DNS points to Vercel's IP range. DNS cleanup (pointing to your own server or a new host) is the only fix — there's no way to disable this from the Vercel side after project deletion. Check both the redirect loop (www → www) and the 404 (apex) when diagnosing.

### API token scope and rotation

- Use a **scoped API token**, not the Global API key. Minimum: `Zone:DNS:Edit` on the specific zone.
- Rotate the token after the task is done. A token shared in a chat session has a indefinite blast radius until revoked.
- If the token was ever visible in a channel, revoke it and create a new one regardless of whether you think it was "just read by the agent."

### Cloudflare content-transformation features can break apps with strict CSP

Cloudflare's edge injects/transforms content in proxied responses by default. Apps that ship their own strict Content-Security-Policy headers (e.g. Cockpit, some SPAs) will break with 403s or CSP violation errors in the browser console.

**Affected settings** (all set via Cloudflare API, `Zone:Settings:Edit` scope):
- `email_obfuscation` — injects anti-spam JS (`/cdn-cgi/email-decode/…`) that CSP blocks
- `server_side_exclude` — hides content from suspected bots, can 403 paths
- `replace_insecure_js` — rewrites `http:` to `https:` in JS source, breaks integrity checks and CSP
- `automatic_https_rewrites` — rewrites `http://` to `https://` in page content
- `rocket_loader` — defer/async script loading that can break app initialization order
- `security_level` — at `medium` or higher, Cloudflare's WAF/challenge pipeline can 403 specific paths

**Fix:**
1. For apps with strict CSP behind Cloudflare proxy, disable all content-transformation features.
2. Strip the app's CSP in the reverse proxy (nginx: `proxy_hide_header Content-Security-Policy;` + `add_header` with permissive policy + `always` flag).
3. Set `security_level` to `low` (or `off` for Enterprise).

See `linux-server-panel/references/cockpit-cloudflare-csp-fix.md` for the full Cockpit-specific recipe.

## Reference

### Native addon / system binary compatibility

- **`references/node-native-addon-abi-mismatch-oracle-linux.md`** — Node.js native addon (`.node` file) compiled for one Node ABI (e.g., Hermes Node v22 → ABI 127) fails to load on the other (Oracle system Node v20 → ABI 115). Covers diagnosis (check `/proc/<pid>/environ`, inspect `.node` header bytes), the rebuild workflow (system `node-gyp` targeting the app's actual Node version, not npm's), and prevention via `NODE_PATH` consistency + symlinks into the app's `node_modules`. Includes the 9router/better-sqlite3 session walkthrough.

### Production Node.js secret length enforcement

- **`references/production-nodejs-secret-length-requirements.md`** — Production Node.js apps that refuse to start with short/default secrets (OpenWA `API_MASTER_KEY` 32-char minimum; `Refusing to start in production: insecure or default value` bootstrap errors). Covers detection (`docker logs --tail`, bootstrap security files), generating compliant secrets (`openssl rand -hex 32`), and setting via runtime env vars instead of `.env` defaults.

- `references/nginx-oracle-linux-runbook.md` — nginx on Oracle Linux 9: install, SELinux context (`httpd_sys_content_t`), boolean (`httpd_can_network_connect`), debug checklist.
- `references/billionmail-oracle-linux-setup.md` — BillionMail self-hosted setup on Oracle Linux 9.
- `references/nginx-subdomain-auth-static-landing.md` — nginx subdomain basic auth pattern.
- `references/9router-tunnel-patterns.md` — Quick tunnel vs named tunnel for 9Router, extracting URLs from cloudflared output.
