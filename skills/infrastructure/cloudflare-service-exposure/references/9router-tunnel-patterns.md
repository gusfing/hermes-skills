# 9Router Tunnel Patterns — Reference

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

1. Login: `cloudflared tunnel login`
2. Create: `cloudflared tunnel create 9router`
3. Route DNS: `cloudflared tunnel route dns 9router 9router.kawaki.co.in`
4. Run: `cloudflared tunnel run 9router`

**Result:** `https://9router.kawaki.co.in`

## Notes

- 9Router listens on port 20128 internally
- Never expose the raw port 20128 directly to the internet
- Always use Cloudflare proxy (orange cloud) or a reverse proxy (nginx) for HTTPS termination

## Example Output

When a quick tunnel is created, cloudflared outputs:
```
INF |  Your quick Tunnel has been created! Visit it at:  |
INF |  https://scoop-investigators-freeze-everywhere.trycloudflare.com              |
```

Extract the URL from this output - do not guess the subdomain.