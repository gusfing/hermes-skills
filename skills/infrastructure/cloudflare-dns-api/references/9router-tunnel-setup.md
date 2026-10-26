---
title: Cloudflare DNS — 9Router tunnel URL setup
---

# Session: 9Router tunnel URL for internet access

**Date:** 2026-10-15
**Zone:** `kawaki.co.in` (ID: `29b3e217548ac234542d3ee0f1b27ae8`)
**Server IP:** `137.23.36.156` (Oracle VPS)
**9Router:** Running on port 20128 (OpenAI-compatible API)

## Current State

- 9Router is accessible at `http://localhost:20128` on the Oracle VPS
- Port 80/443 open for external traffic (nginx listening)
- Existing `router.kawaki.co.in` DNS record already points to Oracle VPS
- Cloudflare API token available: `REDACTED_CLOUDFLARE_TOKEN`

## Tunnel URL Solution

For exposing 9Router to the internet via Cloudflare, you have two options:

### Option 1: Use existing subdomain (preferred)

The DNS record `router.kawaki.co.in` already points to your Oracle VPS. Simply:

1. Configure nginx as reverse proxy for 9Router
2. Set SSL mode to `flexible` (since nginx likely speaks HTTP only)

### Option 2: Create new subdomain

```bash
# Create 9router.kawaki.co.in pointing to Oracle VPS
curl -X POST \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -d '{"type":"A","name":"9router","content":"137.23.36.156","ttl":1,"proxied":true}'
```

This creates: `9router.kawaki.co.in` → `https://9router.kawaki.co.in`

## nginx Reverse Proxy Config for 9Router

```nginx
server {
    listen 80;
    server_name router.kawaki.co.in;  # or 9router.kawaki.co.in

    location / {
        proxy_pass http://127.0.0.1:20128;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_read_timeout 86400s;  # Longer timeout for image generation
        client_max_body_size 100M;   # Allow large image payloads
    }
}
```

## SSL Mode Configuration

Since nginx listens on HTTP port 80 only:

```bash
# Set SSL to flexible (CF ↔ nginx HTTP, CF ↔ client HTTPS)
curl -s -X PATCH \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/ssl" \
  -d '{"value":"flexible"}'
```

## Verification

Test the tunnel:
```bash
curl -s http://router.kawaki.co.in/v1/models | head -c 200
# Should return JSON list of models
```

## Known Limitations

- OCI Oracle VPS blocks outbound SMTP (25, 587, 465) - not relevant for 9Router
- Only ports 80/443 are externally accessible
- 9Router on port 20128 is NOT directly accessible from internet without tunnel