# WhatsApp Dashboard and Tunnels

## Known-working setup

- Dashboard: Node HTTP server on isolated port, e.g. `3001`.
- `/` serves `dashboard/index.html`.
- `/public/qr.png` serves the latest QR screenshot.
- `/api/wa/start` returns immediately; actual WhatsApp launch runs detached.
- `/api/wa/status` returns `{connected, hasQr, qrAgeSeconds}`.

## QR capture flow

1. `chromium.launchPersistentContext(profileDir, { headless: true, userAgent: '<real Chrome UA>' })`
2. `page.goto('https://web.whatsapp.com', { waitUntil: 'networkidle', timeout: 60000 })`
3. Wait 15–25s, then locate `canvas`.
4. `await canvas.screenshot({ path: '<dashboard>/public/qr.png' })`.
5. If no `canvas`, write `NO_QR_FOUND` to logs and retry `/api/wa/start` once.

## Tunnel preference order

1. **localtunnel**: `lt({port})` returns a promise in v2; await it and read `.url`.
2. **Serveo**: `ssh -o StrictHostKeyChecking=no -R 80:localhost:<port> serveo.net`; read public URL from stderr.
   - Remote port `3001` may fail; use `80` or another available remote port.
3. **Direct IP**: `http://<public-ip>:<port>/`. Often blocked by provider firewall; use as fallback only.

## Caveats

- Do not block the HTTP handler while launching WhatsApp; use detached process.
- In this container, `browser_snapshot`/`browser_vision` against Chrome CDP WhatsApp tab can time out even when the tab is loaded. If that happens twice, switch to Playwright persistent context and don’t retry CDP.
- Loading screen, QR page, and chat list are distinct page states; inspect/diff them before deciding the session is stuck.
