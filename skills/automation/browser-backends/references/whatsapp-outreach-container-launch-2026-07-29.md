# WhatsApp Outreach — Container Launch Notes 2026-07-29

## Verified environment

- Container host with Xvfb installed
- No system Chrome binary in `/usr/bin`
- Playwright-downloaded Chromium at `/opt/data/.playwright/chromium-1234/chrome-linux64/chrome`
- Camofox/Camoufox fails at launch:
  - `libgtk-3.so.0` missing
  - `Sandbox: CanCreateUserNamespace() clone() failure: EPERM`
- Port 9222 used for CDP
- Profile dir pattern: `/opt/data/chrome-profiles/wa_<account_id>`

## Verified sequence

1. `mkdir -p /opt/data/chrome-profiles/wa_account_a`
2. `PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright HOME=/opt/data npx playwright install chromium`
3. `templates/chrome-cdp-social-launcher.sh /opt/data/chrome-profiles/wa_account_a 9222 :99`
4. `curl -s http://127.0.0.1:9222/json/version` → confirms UA, browser version
5. `curl -s http://127.0.0.1:9222/json/list | python3 -m json.tool` → find tab id
6. Hit QR login screen first time; user scans with phone
7. After login, verify with CDP evaluation:
   - look for `hasChatList: true`
   - look for `hasQR: false`

## UA requirement

WhatsApp Web blocks when UA contains `HeadlessChrome`.
Use a normal desktop Chrome UA string on every launch.

## Hermes browser config caveat

Hermes browser config is read at startup. Changing `browser.provider`,
`browser.cdp_url`, or similar keys in `config.yaml` mid-session does
NOT hot-reload the browser provider.

If `browser_navigate` returns `503 ... http://localhost:9377/tabs` after
setting `browser.provider=cdp`, restart Hermes rather than retrying.

## First-send blockers observed

- `error: "Refusing to write ... manifest.yaml": YAML document start required` → lead with `---` or omit YAML frontmatter when writing non-skill YAML
- script runs need `node_modules/ws` locally under `/opt/data/outreach/node_modules`
- `SingletonLock` prevents relaunching Chrome with same profile dir
