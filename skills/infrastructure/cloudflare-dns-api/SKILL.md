---
name: cloudflare-dns-api
description: Manage Cloudflare DNS, SSL, and fix redirect loops via API.
---

# Cloudflare DNS API

Programmatic Cloudflare DNS: zone lookup, record CRUD, SSL mode changes, proxied-vs-unproxied decisions, redirect-loop debugging. No dashboard.

## Prerequisites

API token (not global key). Scope: `Zone:DNS:Edit` + `Zone:Settings:Edit`.

```bash
export CF_TOKEN="your-api-token"  # used in every curl below

# Get zone ID by domain name
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones?name=yourdomain.com" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['id'])"
```

Save the zone ID — every call below needs it.

## Record CRUD

### List all records

```bash
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" | python3 -c "
import sys,json
for r in json.load(sys.stdin)['result']:
    print(f\"{r['type']:6} {r['name']:30} → {r['content']:30} proxied={r.get('proxied',False)}\")
"
```

### List by name

```bash
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=sub.yourdomain.com"
```

### Create A record (proxied / orange cloud ON)

```bash
curl -s -X POST \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -d '{"type":"A","name":"sub","content":"SERVER_IP","ttl":1,"proxied":true}'
```

### Create CNAME (proxied)

```bash
curl -s -X POST \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -d '{"type":"CNAME","name":"sub","content":"target.domain","ttl":1,"proxied":true}'
```

### Delete by ID

```bash
curl -s -X DELETE \
  -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID"
```

### Bulk delete all records matching a name

```bash
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=sub.yourdomain.com" | python3 -c "
import sys,json,urllib.request
d=json.load(sys.stdin)
for r in d['result']:
    req = urllib.request.Request(
        f'https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/{r[\"id\"]}',
        method='DELETE',
        headers={'Authorization': 'Bearer $CF_TOKEN'}
    )
    urllib.request.urlopen(req)
    print(f'Deleted {r[\"type\"]} {r[\"name\"]} → {r[\"content\"]}')
"
```

## SSL/TLS Mode

### Check mode

```bash
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/ssl" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['value'])"
```

### Set mode

```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/ssl" \
  -d '{"value":"flexible"}'  # off | flexible | full | full_strict
```

| Mode | CF→Origin | When |
|------|-----------|------|
| `off` | HTTP | Avoid |
| `flexible` | HTTP | Origin speaks HTTP only (nginx:80, no TLS) — fixes 521 |
| `full` | HTTPS (self-signed OK) | Origin has HTTPS, no CA cert needed |
| `full_strict` | HTTPS (CA cert required) | Origin has valid Let's Encrypt / CA cert |

**521 fix:** If nginx listens on port 80 only (no TLS) and Cloudflare SSL=`full`, Cloudflare sends HTTPS to port 80 → connection fails → 521. Set SSL=`flexible`.

## Proxied vs Unproxied

- **Proxied (`true`)**: Cloudflare in front. Visitors see CF IPs. CF handles TLS/DDoS/caching. Use for public subdomains.
- **Unproxied (`false`)**: DNS resolves directly to origin IP. No CF in path. Use when origin must see real IPs without `X-Forwarded-For`, or origin handles its own TLS.

**Redirect loop pitfall:** Root CNAME → Vercel (redirects root→www), while www is A record → CF proxy IPs (CF returns 308 to itself). Fix: make www point directly to Vercel's IPs as A records with proxy OFF, matching what root resolves to.

## Error Reference

### 521 — Web Server Is Down

CF reaches origin but origin errors. Check: SSL mode (if `full` but origin is HTTP-only → switch to `flexible`), origin response code (`curl -sI https://domain/`), nginx server block matching the Host header.

### 522 — Connection Timed Out

CF cannot reach origin. Check: cloud provider firewall (OCI Security Lists, AWS SGs), nginx running + listening on correct port, DNS IP correct, NSG (OCI) overriding security list.

### ERR_TOO_MANY_REDIRECTS

Infinite loop. Check: root + www DNS contradiction (one proxied, one unproxied, different origins), HTTPS redirect loop (origin redirects HTTP→HTTPS but CF connects HTTP under `flexible` mode), CNAME chain breaking at Cloudflare proxy.

## Zone Settings (features that silently break web apps)

Cloudflare's zone settings API controls features that inject/rewrite HTML, JS, and headers — often breaking self-hosted apps behind the proxy. Query and toggle these at:

```
GET  /zones/{zone_id}/settings                 # list all settings
GET  /zones/{zone_id}/settings/{setting_id}   # single setting
PATCH /zones/{zone_id}/settings/{setting_id}  # toggle setting
     -d '{"value":"<new_value>"}'
```

### Common offenders for self-hosted apps

| Setting ID | Default | Problem | Fix |
|---|---|---|---|
| `email_obfuscation` | on | Injects JS that violates CSP (`script-src` blocks it) | `"value":"off"` |
| `server_side_exclude` | on | Wraps content in JS that breaks CSP nonce/hash checks | `"value":"off"` |
| `replace_insecure_js` | on | Rewrites `http:` → `https:` in inline scripts; breaks CSP for non-TLS origins | `"value":"off"` |
| `automatic_https_rewrites` | on | Same as above — rewrites insecure URLs in HTML/JS | `"value":"off"` |
| `security_level` | medium | Challenges/rates-limits based on perceived threat; can 403 legitimate requests | `"value":"low"` (off requires Enterprise) |
| `minification` | off | Minifies HTML/JS/CSS; can break apps relying on exact formatting | `"value":"off"` |
| `browser_check` | on | Challenges browsers that don't pass JS check | `"value":"off"` for API backends |

**Response shape** — success: `{"result":{"value":"off",...},"success":true}`. Error (setting ID wrong or not editable): `{"errors":[{"code":1003,"message":"Undefined zone setting: X"}],"result":null}`.

**Note:** Setting IDs differ from display names. Query `/zones/{id}/settings` to find the exact ID for any feature. Some settings are not editable via API (returns `editable:false`).

### Debugging: "works direct, 403/CSP error via Cloudflare"

When an app works on the origin IP but fails through Cloudflare with CSP violations or 403s:

1. Check which Cloudflare setting is injecting: `curl -sI https://domain/` and look for modified headers, added JS sources in the HTML
2. Compare direct (`curl -sI http://origin_ip:port/`) vs proxied — diff the HTML/headers
3. Disable settings one at a time via API, test after each
4. Common culprits: `email_obfuscation` (adds `beacon.min.js`), `replace_insecure_js` (modifies inline scripts), `server_side_exclude` (wraps with challenge JS)

### CSP with Cloudflare proxy

If your origin sends a restrictive CSP and Cloudflare injects scripts (beacon, obfuscation, etc.), the browser blocks them. Solutions in order of preference:

1. **Fix origin CSP** — make it permissive enough for Cloudflare's injected resources, or
2. **Disable Cloudflare features** that inject content (see table above), or
3. **Strip/replace CSP at nginx** — `proxy_hide_header Content-Security-Policy` + `add_header Content-Security-Policy "..." always` to control it at the proxy layer

`script-src * 'unsafe-inline'` permits all inline `<script>` blocks — SHA-256 hashes in addition to `'unsafe-inline'` are redundant and harmless. If the browser still reports "invalid source" for a hash, the hash doesn't match the actual script — regenerate it from the live content, or just rely on `'unsafe-inline'`.

## nginx reverse proxy config (for subdomain → local service)

```nginx
server {
    listen 80;
    server_name sub.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:LOCAL_PORT;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        proxy_read_timeout 86400s;
    }
}
```

DNS: A record `sub → server_IP`, proxied=true. SSL: `flexible` if nginx has no TLS; `full` if nginx has self-signed cert on 443.

## Post-third-party-deletion DNS cleanup

When a third-party hosting project (Vercel, Netlify, etc.) is deleted, residual DNS records often keep pointing to the dead third-party infrastructure. This causes 404s, 521s, or redirect loops even though the records "look right" in the dashboard.

**Symptoms after deletion:**
- Apex domain returns 404 `DEPLOYMENT_NOT_FOUND` from the third party
- www subdomain does a redirect loop (third-party default redirect for unmatched domains)
- Records still exist in Cloudflare pointing to third-party IPs or CNAMEs

**Cleanup procedure:**

1. **Enumerate ALL records pointing to the third party:**
   ```bash
   curl -s -H "Authorization: Bearer $CF_TOKEN" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" | python3 -c "
   import sys,json
   d=json.load(sys.stdin)
   for r in d['result']:
       if 'vercel' in r.get('content','').lower() or 'netlify' in r.get('content','').lower():
           print(f'{r[\"type\"]:6} {r[\"name\"]:30} → {r[\"content\"]:45} ID={r[\"id\"]}')
   "
   ```
   Also check for: apex CNAME (overrides A record), wildcard A records (`*.domain.com`), www A records, and any CNAME at `www`.

2. **Delete ALL matching records by ID** (don't rely on name filters — a CNAME at apex or a wildcard will shadow your new A records):
   ```bash
   curl -s -X DELETE \
     -H "Authorization: Bearer $CF_TOKEN" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID"
   ```

3. **Purge Cloudflare cache:**
   ```bash
   curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
     -d '{"purge_everything":true}'
   ```

4. **Recreate fresh A records pointing to your server:**
   ```bash
   curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
     -d '{"type":"A","name":"kawaki.co.in","content":"YOUR_SERVER_IP","ttl":1,"proxied":true}'
   curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
     -d '{"type":"A","name":"www","content":"YOUR_SERVER_IP","ttl":1,"proxied":true}'
   ```
   Create separate records for apex and www — don't use a CNAME for www pointing to apex when both need proxy (the CNAME chain can break at the Cloudflare proxy layer).

5. **Verify from multiple DNS resolvers** (8.8.8.8, 1.1.1.1, Cloudflare NS):
   ```bash
   dig @8.8.8.8 yourdomain.com A +short
   dig @1.1.1.1 www.yourdomain.com A +short
   ```

### Why a fresh record ID matters

Cloudflare assigns proxy IPs asynchronously when you create or toggle a proxied record. After deleting and recreating the same record, public DNS resolvers may still return the old proxy IPs for several minutes. Creating a **new** record (delete old → purge → create new with different ID) forces Cloudflare to assign fresh proxy IPs. Toggling `proxied` on/off on the same record sometimes fails to flush the assignment.

### CNAME at apex overrides A record

A CNAME at the zone apex (`kawaki.co.in` CNAME → something) takes precedence over any A record at the same name. If a third-party setup created an apex CNAME and you later add an A record, the CNAME wins and your A record is invisible to resolvers. Always check for and delete apex CNAMEs when cleaning up.

## Third-party redirect handling (Vercel, Netlify)

When root is CNAME → third-party and you want www to work without loops:

## References

- `references/kawaki-co-in-mail-setup.md` — kawaki.co.in mail DNS setup (Hostinger relay configuration)
- `references/9router-tunnel-setup.md` — Exposing 9Router to internet via Cloudflare tunnel
