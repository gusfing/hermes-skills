# Dashboard & Sharing Setup — Reference

## Quick Tunnel (Ephemeral)
```bash
# Serve dashboard directory
cd /home/opc/carousel-dashboard
python3 -m http.server 8090 --bind 0.0.0.0 &

# Expose via Cloudflare quick tunnel
cloudflared tunnel --url http://127.0.0.1:8090
# URL rotates on restart — e.g., https://paint-journalism-arctic-receptors.trycloudflare.com/
# New session URL: https://namely-amounts-penny-dana.trycloudflare.com/
```

## Dashboard Structure
```
/carousel-dashboard/
├── index.html          # Main dashboard (dark theme, grid of cards)
├── carousel.zip        # All 7 PNGs + HTML source
├── claude-code-carousel.html  # HTML source
├── claude-code-carousel_1.png  # Slide 1
├── claude-code-carousel_2.png  # Slide 2
├── claude-code-carousel_3.png  # Slide 3
├── claude-code-carousel_4.png  # Slide 4
├── claude-code-carousel_5.png  # Slide 5
├── claude-code-carousel_6.png  # Slide 6
└── claude-code-carousel_7.png  # Slide 7
```

## Direct File URLs (from quick tunnel)
- Dashboard: `https://<tunnel>.trycloudflare.com/`
- ZIP: `https://<tunnel>.trycloudflare.com/carousel.zip`
- HTML: `https://<tunnel>.trycloudflare.com/claude-code-carousel.html`
- Slide N: `https://<tunnel>.trycloudflare.com/claude-code-carousel_N.png`

## Named Tunnel (Permanent)
For production use, create a named tunnel:
```bash
cloudflared tunnel login
cloudflared tunnel create carousel-dashboard
cloudflared tunnel route dns carousel-dashboard carousel.yourdomain.com
cloudflared tunnel run --url http://127.0.0.1:8090 carousel-dashboard
```

## Dashboard Features
- Dark theme (#0f0f0f background)
- Responsive grid (min 340px cards)
- Each slide card: preview image + title/subtitle + download link
- Xiaohei illustrations strip (source images)
- Download buttons: ZIP (all) + individual PNGs
- Handle branding (@kunalsharmadec6)
- No JS dependencies — pure HTML/CSS

## Working Example (Session)
- Tunnel: https://namely-amounts-penny-dana.trycloudflare.com/ (current)
- Previous: https://paint-journalism-arctic-receptors.trycloudflare.com/
- All 7 slides exported at 1080x1350
- ZIP size: ~382 KB
- HTML source included for re-export

## Pitfalls
- **Server binding** -> Must use `--bind 0.0.0.0` (not 127.0.0.1) for Cloudflare Tunnel to reach it
- **Quick tunnel rotation** -> trycloudflare.com URLs change on process restart; use named tunnel for permanence
- **Port conflict** -> Kill existing python3 http.server on 8090 before restart: `pkill -f "http.server 8090"`