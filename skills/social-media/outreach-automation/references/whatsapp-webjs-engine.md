# whatsapp-web.js standalone engine notes
- Install: `npm install whatsapp-web.js qrcode-terminal`
- Primary use: standalone WhatsApp outreach engine when Playwright CDP is unavailable.
- Auth: local `.wwebjs_auth` directory; reuse across runs.
- QR: first run requires manual scan; do not reuse cached QR.
- Container args: `--no-sandbox --disable-gpu --disable-dev-shm-usage`.
- Ban mitigations: 30–90s randomized delays, <=40 contacts/day, <=3 template variants, warmup <=10 in first 24h, avoid group blasts.
