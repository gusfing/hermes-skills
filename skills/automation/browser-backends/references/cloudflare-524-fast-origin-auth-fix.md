# Cloudflare 524 when origin is actually fast

## Symptom

- Cloudflare returns HTTP 524: `origin_response_timeout`
- Provider/gateway reports: `Gateway was unreachable`, `The operation was aborted due to timeout`
- Actual origin responds in ~3ms with 401/403/404

This means the failure is **not** the tunnel, VPN, or origin speed.
It is almost always a **provider config mismatch**: wrong path, missing API key, or wrong auth header.

## Diagnostic sequence

1. Curl the origin directly and compare timing
   ```bash
   curl -s -o /tmp/check.txt -w 'HTTP:%{http_code}\nTIME:%{time_total}s\n' http://127.0.0.1:<port>/v1/messages
   ```
2. Curl through the public tunnel
   ```bash
   curl -s -o /tmp/check2.txt -w 'HTTP:%{http_code}\nTIME:%{time_total}s\n' https://<tunnel>.trycloudflare.com/v1/messages
   ```
3. If both return the same status in <1s, the network is fine.
   The client is likely retrying an invalid path or getting auth rejected
   repeatedly, which cancels the request before Cloudflare's proxy read timeout.

## Common mismatches seen with 9router

- Wrong path: `/v1/v1/messages` instead of `/v1/messages`
- Missing API key: 9router returns `401: API key required for remote API access`
- Wrong auth format: header must be `x-api-key`, `Authorization: Bearer`, or `Authorization: Token`

## Fix

Correct the provider config:
- Base URL: the tunnel or direct origin URL
- API path: exact path shown in the app's API routes, e.g. `/v1/messages`
- Auth: include the API key in the header the app expects

Once the origin returns 200 instead of 401, retries stop and the Cloudflare 524 disappears.

## cloudflared quick tunnel notes

- Quick tunnels need no Cloudflare account login
- Command: `cloudflared tunnel --url http://localhost:<port>`
- Hostname is random and can change later
- For stable URLs, use named tunnels after `cloudflared tunnel login`
