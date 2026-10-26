---
title: Cloudflare DNS — kawaki.co.in post-Vercel-deletion cleanup
---

# Session: kawaki.co.in post-Vercel-deletion cleanup

**Date:** 2026-09-20
**Zone:** `kawaki.co.in` (ID: `29b3e217548ac234542d3ee0f1b27ae8`)
**Account:** `8d52aa91028e665b3fdbb4755662efb8` (Ks05460@gmail.com's Account)
**Server IP:** `137.23.36.156` (nginx + 9router on port 20128)
**CF Token used:** `REDACTED_CLOUDFLARE_TOKEN` — rotated out of session after use

## What happened

1. Vercel project `kawaki.co.in` was deleted.
2. `kawaki.co.in` apex still had a CNAME → `0821f3977749886c.vercel-dns-017.com` (unproxied). Root returned 404 `DEPLOYMENT_NOT_FOUND`.
3. `www.kawaki.co.in` had A records pointing to Vercel IPs (`216.198.79.1`, `64.29.17.1`) with proxy OFF. Vercel returned 308 redirect loop (`www → www`).
4. Wildcard `*.kawaki.co.in` A records pointed to Vercel IPs with proxy ON — these would catch any unconfigured subdomain and route it to dead Vercel infra.

## Cleanup performed (step by step)

### 1. Deleted apex CNAME (kawaki.co.in → vercel)
```
DELETE /zones/29b3e217548ac234542d3ee0f1b27ae8/dns_records/71e745f228b643d21d4ea7a192b774b9
```
ID from: `curl .../dns_records?name=kawaki.co.in&type=CNAME`

### 2. Deleted www A records → Vercel IPs
```
DELETE .../dns_records/2a322304421eb216c3d88ef3a33d6484   (64.29.17.1)
DELETE .../dns_records/d4d8d43555d563590112808fa6faa511   (216.198.79.1)
```

### 3. Deleted wildcard A records → Vercel IPs
```
DELETE .../dns_records/e9cdc63a6b8e6147e59a37b418fc6809   (*.kawaki.co.in → 64.29.17.65)
DELETE .../dns_records/c1fadafe669b0cf1e510d90a6318ebc6   (*.kawaki.co.in → 216.198.79.1)
```

### 4. Purged Cloudflare cache
```
POST /zones/29b3e217548ac234542d3ee0f1b27ae8/purge_cache
{"purge_everything": true}
```

### 5. Created fresh A records → 137.23.36.156 (proxied)
```
POST .../dns_records
  apex:   {"type":"A","name":"kawaki.co.in","content":"137.23.36.156","ttl":1,"proxied":true}
         → ID: 23f9b32b56360ef7868bf4a22d7000b3

  www:    {"type":"A","name":"www","content":"137.23.36.156","ttl":1,"proxied":true}
         → ID: acd0cdffab6e8e5a2442f90ad781046d
```

### 6. Created www as CNAME → apex (later)
```
POST .../dns_records
  {"type":"CNAME","name":"www","content":"kawaki.co.in","ttl":1,"proxied":true}
  → ID: ee20eef7245622bbb91b861b9d971e26
```

### 7. Set Cloudflare SSL mode to flexible
```
PATCH /zones/29b3e217548ac234542d3ee0f1b27ae8/settings/ssl
{"value":"flexible"}
```
Was `full` (caused 521 because nginx only speaks HTTP on port 80, no TLS).

## Verification

- `kawaki.co.in` → HTTP 200 (Cloudflare → nginx:80 → 9router:20128 → login page)
- `www.kawaki.co.in` → HTTP 200 (CNAME → apex, same path)
- Both return nginx headers with 9router login page content

## Key learnings

### Cleanup must enumerate ALL records — name filters miss shadowers

After deleting the Vercel project, just deleting `www` A records wasn't enough:
- Apex CNAME (`kawaki.co.in → vercel-dns-017.com`) was shadowing the new apex A record
- Wildcard `*.kawaki.co.in` A records would catch any subdomain not explicitly configured
- The www CNAME created as `www.kawaki.co.in.kawaki.co.in` (double-qualified) — created by API with name="www" and content="kawaki.co.in" but Cloudflare interpreted it as a fully-qualified CNAME. Must delete and recreate carefully.

### Cloudflare proxy IP assignment is async — recreate for fresh IPs

After deleting and recreating the same www A record at `137.23.36.156`, public DNS resolvers (8.8.8.8, 1.1.1.1) still returned Vercel's proxy IPs (`216.198.79.1`, `64.29.17.1`) — not the new CF proxy IPs. Creating a CNAME instead (www → apex) resolved it because the CNAME follows the apex's fresh proxy assignment.

### Proxy toggle on same record sometimes fails to flush

Setting `proxied: false` then `proxied: true` on the same record ID didn't cause Cloudflare to re-assign proxy IPs. Public DNS kept resolving to Vercel IPs. Deleting + recreating with new ID is the reliable path.

### CNAME at apex overrides A record

When both exist at the same name, the CNAME wins and the A record is invisible. The apex CNAME created by Vercel's setup was still present after the project was deleted — it had to be explicitly deleted before the new apex A record could take effect.

## Commands used

Full API token: `REDACTED_CLOUDFLARE_TOKEN` (rotated — see memory)

Key curl patterns:
```bash
# List all records
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records"

# List by name + type
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=www.kawaki.co.in&type=CNAME"

# Delete by ID
curl -s -X DELETE -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID"

# Purge cache
curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -d '{"purge_everything":true}'

# Set SSL mode
curl -s -X PATCH -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/ssl" \
  -d '{"value":"flexible"}'
```

## Remaining state

- `mail.kawaki.co.in` → `147.93.96.248` (unproxied, for Zoho mail) — untouched, still valid
- `wa.kawaki.co.in` → `137.23.36.156` (proxied, OpenWA) — untouched, still valid
- `router.kawaki.co.in` → `137.23.36.156` (proxied, 9router) — untouched, still valid
- SPF/DKIM/DMARC TXT records, CAA records, MX record — all preserved
- Google site verification TXT — preserved
- Zoho verification TXT — preserved
