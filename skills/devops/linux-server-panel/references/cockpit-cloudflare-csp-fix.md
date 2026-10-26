# Cockpit + Cloudflare Proxy — CSP Beacon Fix

## Problem

When Cockpit is exposed behind Cloudflare's proxy (orange cloud), multiple things break:

1. **Cloudflare injects `beacon.min.js`** from `https://static.cloudflareinsights.com` into the HTML response. Cockpit's own CSP header is strict and blocks it — browser console shows:
   ```
   Loading the script 'https://static.cloudflareinsights.com/beacon.min.js/...' 
   violates the following Content Security Policy directive: 
   "default-src 'self' http://panel.kawaki.co.in 'unsafe-inline'"
   ```

2. **Cloudflare's transformation features** (email obfuscation, server-side exclude, replace-insecure-js, automatic HTTPS rewrites) rewrite/transform the HTML at the edge, which can cause `403 Forbidden` on Cockpit paths like `/cockpit/login`. The server response is `fatal: Forbidden` from `login.js`.

3. **Cockpit's own CSP** (`default-src 'self' http://panel.kawaki.co.in`) also blocks WebSocket upgrades and any resource not explicitly listed — even without Cloudflare, if you proxy through nginx you need to relax this.

## Root cause

Cloudflare's edge modifies the HTML/JS response for proxied domains by default. Cockpit (a RHEL/Fedora project) ships with a tight CSP designed for direct access, not for sitting behind a CDN that injects scripts.

## Fix — step by step

### Step 1: Disable Cloudflare zone features that modify content

These Cloudflare settings inject or transform code in proxied responses. All must be `off` for Cockpit to work cleanly:

```bash
# Email Obfuscation — injects anti-spam JS that breaks CSP
curl -s -X PATCH \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/email_obfuscation" \
  -d '{"value":"off"}'

# Server Side Exclude — hides content from suspected bots, can 403 paths
curl -s -X PATCH \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/server_side_exclude" \
  -d '{"value":"off"}'

# Replace Insecure JS — rewrites http: to https: in JS, breaks CSP
curl -s -X PATCH \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/replace_insecure_js" \
  -d '{"value":"off"}'

# Automatic HTTPS Rewrites — rewrites http:// to https:// in page content
curl -s -X PATCH \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/automatic_https_rewrites" \
  -d '{"value":"off"}'
```

**Note:** `security_level` set to `off` is Enterprise-only. For non-Enterprise, use `low`:
```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/security_level" \
  -d '{"value":"low"}'
```

### Step 2: Strip and replace CSP in nginx

Cockpit sends its own CSP header. nginx `add_header` alone won't override it (Cockpit's header comes from the upstream). Use `proxy_hide_header` to strip it, then add your own:

```nginx
server {
    listen 80;
    server_name panel.example.com;

    location / {
        proxy_pass http://127.0.0.1:9090;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;

        # Strip Cockpit's restrictive CSP
        proxy_hide_header Content-Security-Policy;
        proxy_hide_header X-Frame-Options;
        proxy_hide_header X-Content-Type-Options;
        proxy_hide_header X-XSS-Protection;
        proxy_hide_header Strict-Transport-Security;

        # Add permissive CSP that allows Cloudflare beacon and all external resources
        add_header Content-Security-Policy "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; script-src * 'unsafe-inline' 'unsafe-eval'; connect-src * ws: wss:; img-src * data:; style-src * 'unsafe-inline'; font-src *; object-src *; frame-src *;" always;
    }

    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

Key directives:
- `proxy_hide_header Content-Security-Policy;` — removes Cockpit's upstream CSP
- `add_header ... always;` — the `always` flag is critical; without it, nginx won't add the header on error responses (401, 403)
- `proxy_set_header Upgrade` + `Connection "upgrade"` — WebSocket support (Cockpit terminal, live updates)

### Step 3: Handle `/cockpit/` path prefix routing

Cockpit serves its SPA at paths like `/cockpit/login`, `/cockpit/assets/index-xxx.js`, `/cockpit/styles/main.css`. When nginx proxies with `location /`, it passes the full URI to the backend — Cockpit on port 9090 already expects `/cockpit/`-prefixed paths, so this is correct. **Do NOT strip the prefix.**

```nginx
location / {
    proxy_pass http://127.0.0.1:9090;   # NO trailing slash — pass URI as-is
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;

    proxy_hide_header Content-Security-Policy;
    add_header Content-Security-Policy "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; script-src * 'unsafe-inline' 'unsafe-eval'; connect-src * ws: wss:; img-src * data:; style-src * 'unsafe-inline'; font-src *; object-src *; frame-src *;" always;
}
```

**Critical:** Using `location /cockpit/ { proxy_pass http://127.0.0.1:9090/; }` (with trailing slash to strip prefix) is **WRONG** for Cockpit — it causes all asset requests (`/cockpit/static/login.js`, `/cockpit/styles/main.css`) to hit the backend without the `/cockpit/` prefix, returning 404 HTML instead of the actual JS/CSS files (browser shows `MIME type 'text/html' is not a supported stylesheet`). This was verified empirically: `curl -I http://127.0.0.1:9090/cockpit/static/login.js` should return `Content-Type: application/javascript`; if it returns `text/html`, the path is wrong.

The `location /` approach (pass URI as-is) is correct because Cockpit's backend on port 9090 already serves its SPA under the `/cockpit/` path prefix internally — it expects `/cockpit/login`, `/cockpit/assets/*`, etc. as-is.

### Step 4: Verify

```bash
# Without auth — should get 401
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://panel.example.com/

# With auth — should get 200 (Cockpit login page)
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 -u user:pass http://panel.example.com/

# Check CSP header is the permissive one
curl -sv --connect-timeout 5 -u user:pass http://panel.example.com/ 2>&1 | grep -i "Content-Security-Policy"

# Check key Cockpit paths
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 -u user:pass http://panel.example.com/cockpit/login
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 -u user:pass http://panel.example.com/cockpit/assets/index-xxx.js
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 -u user:pass http://panel.example.com/cockpit/styles/main.css
```

Expected: all 200 with auth, 401 without. CSP header should be the permissive one from nginx, not Cockpit's restrictive one.

### Step 5: Cloudflare cache purge (if previous broken responses were cached)

If Cloudflare cached a broken response (403 or CSP-blocked page) before the fix, purge the cache:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -d '{"purge_everything":true}'
```

## Diagnostic checklist

| Symptom | Likely cause | Check |
|---------|-------------|-------|
| Browser console: `violates CSP directive` for `beacon.min.js` | Cockpit CSP too strict + Cloudflare beacon injection | Check nginx CSP header; disable Cloudflare features |
| `/cockpit/login` returns 403 | Cloudflare `security_level` too high, or transformation features blocking | Set security_level to low; disable email_obfuscation, server_side_exclude, replace_insecure_js |
| `/cockpit/login` returns 404 | nginx proxy_pass missing trailing slash (path not stripped) | Use `proxy_pass http://127.0.0.1:9090/;` (with trailing slash) |
| Direct IP:9090 times out | Port 9090 blocked at firewall/NSG (normal) | Use nginx proxy on port 80; don't debug 9090 directly |
| Cockpit login page loads but terminal doesn't connect | Missing WebSocket proxy headers | Add `Upgrade`/`Connection` headers in nginx |
| CSP header still shows Cockpit's restrictive value | `add_header` without `proxy_hide_header` (nginx add_header doesn't override upstream headers) | Add `proxy_hide_header Content-Security-Policy;` before `add_header` |
| Fix applied but still seeing old behavior | Cloudflare cached broken response | Purge cache (`purge_everything: true`) |

## What NOT to do

- **Don't `setenforce 0`** for SELinux issues — use the `httpd_can_network_connect` boolean.
- **Don't rely on `add_header` alone** to override upstream CSP — it appends, doesn't replace. Use `proxy_hide_header` first.
- **Don't leave Cloudflare transformation features on** for any app that ships its own CSP — they will fight.
- **Don't skip the `always` flag** on `add_header` — without it, error responses (401, 403) won't get the CSP header, and the browser may fall back to a stricter default.

## See also

- `references/cockpit-nginx-exposure.md` — general Cockpit nginx exposure (WebSocket headers, htpasswd via openssl, basic auth)
- `cloudflare-service-exposure/SKILL.md` — Cloudflare DNS, SSL, proxy settings, WAF
