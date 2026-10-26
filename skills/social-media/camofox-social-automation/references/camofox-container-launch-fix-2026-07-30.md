# Camofox Container Launch Fix — 2026-07-30

## Root cause
Two blockers inside Docker/LXC container:
1. `libgtk-3.so.0` missing → installing `libgtk-3-0t64` and GTK stack fixed it
2. Sandbox `clone(CLONE_NEWUSER) EPERM` → container kernel restriction; browsers need `--no-sandbox` or proper seccomp/apparmor profile

## Working apt-get install command (run as root in container)
```bash
apt-get update && apt-get install -y \
  libgtk-3-0t64 \
  libdbus-glib-1-2 \
  libx11-xcb1 \
  libxtst6 \
  libxss1 \
  libasound2t64 \
  libnss3 \
  libxcb-dri3-0 \
  libdrm2 \
  libgbm1 \
  libxcomposite1 \
  libxdamage1 \
  libxi6 \
  libcups2t64 \
  libatk1.0-0t64 \
  libatk-bridge2.0-0t64 \
  libpango-1.0-0 \
  libcairo2 \
  libxrandr2 \
  libatspi2.0-0t64 \
  xvfb
```

Note: Debian `t64` transition packages; names may differ on Ubuntu/Debian 12.

## Health probe Workaround

Symptom: `Protocol error (Browser.setDefaultViewport)` / `isMobile` schema mismatch
in `browser.newContext()` health probe.

Temporary fix: patch `server.js` health probe block to suppress `setDefaultViewport|isMobile`
errors and avoid restart loop:

```js
if (/setDefaultViewport|isMobile/.test(msg)) {
  log('info', 'health probe suppressed...', { timeSinceSuccessMs: timeSinceSuccess });
} else {
  restartBrowser('health probe failed').catch(() => {});
}
```

Long-term fix: pin `camoufox-js` to a compatible version or Patch upstream.

## Verified state
- Camofox launches successfully with GTK libs installed
- Tab creation works: `POST /tabs {"userId":"x_account_a","sessionKey":"x_account_a","url":"https://x.com"}`
- X composer refs present: `link "Post" [e17]`, `button "Account menu" [e18]`, `textbox "Post text" [e35]`
- Composer still sometimes redirects back to `/home`; use JS opener before changing backends
