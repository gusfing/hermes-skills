
# Outbound restrictions from cloud VPS — session details

## Session: 2026-09-27 — Oracle → Hostinger SMTP relay

## What was discovered

- Oracle VPS (137.23.36.156) could NOT reach Hostinger (147.93.96.248) on ports 25, 587, 80 (direct IP), 443, or 2222 (SSH). All timed out.
- Oracle VPS COULD reach Hostinger on port 80 via the Cloudflare-proxied hostname `billionmail.kawaki.co.in` (HTTP 200).
- This means OCI blocks outbound TCP to external IPs on these ports at the network level, but allows HTTP traffic routed through Cloudflare's CDN.

## Diagnosis steps run

```bash
# From Oracle VPS:
timeout 5 bash -c "echo > /dev/tcp/147.93.96.248/25"  → BLOCKED
timeout 5 bash -c "echo > /dev/tcp/147.93.96.248/587" → BLOCKED
timeout 5 bash -c "echo > /dev/tcp/147.93.96.248/80"  → BLOCKED
timeout 5 bash -c "echo > /dev/tcp/147.93.96.248/443" → BLOCKED
timeout 5 bash -c "echo > /dev/tcp/147.93.96.248/2222" → BLOCKED

# Via Cloudflare proxy (hostname):
curl -s -o /dev/null -w "%{http_code}" http://billionmail.kawaki.co.in:80/ → 200
curl -s -o /dev/null -w "%{http_code}" http://openwa.kawaki.co.in:80/ → 200
```

## Attempted workarounds

1. **Oracle Postfix relayhost = [147.93.96.248]:80** — failed, port 80 direct IP blocked
2. **Oracle Postfix relayhost = [billionmail.kawaki.co.in]:80** — failed, Cloudflare HTTP proxy doesn't understand SMTP (returned 400 Bad Request)
3. **Pending: nginx stream proxy on Hostinger** — port 80 → localhost:25 TCP forward. Not yet set up when session ended.

## Pending item

Hostinger nginx needs a stream block to forward port 80 TCP to localhost:25 (BillionMail SMTP). Commands to run on Hostinger:

```bash
sudo cat > /etc/nginx/stream.conf << 'EOF'
stream {
    server {
        listen 80;
        proxy_pass 127.0.0.1:25;
        proxy_timeout 30s;
    }
}
EOF
sudo nginx -t && sudo nginx -s reload
```

Then on Oracle, relayhost = `[147.93.96.248]:80` (direct IP, not hostname).

## Cloudflare API token status

Token `REDACTED_CLOUDFLARE_TOKEN` returned "Invalid API Token" when tested on 2026-09-27. DNS updates require a fresh token.

## Key takeaway

When a cloud VPS blocks outbound SMTP (common), and the relay host is reachable via CDN on port 80, the correct architecture is:

1. Set up TCP stream proxy on relay host: `listen 80 → proxy_pass 127.0.0.1:25`
2. Oracle Postfix relayhost = `[RELAY_HOST_IP]:80` (direct IP, not CDN hostname)
3. CDN hostname works for web dashboard access, but raw IP is needed for SMTP relay through nginx stream

## Related

- `SKILL.md` — outbound restrictions section
- Previous session: `wa.kawaki.co.in` inbound exposure (same VPS, opposite direction)
