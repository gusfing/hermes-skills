# WhatsApp outreach via Playwright-downloaded Chromium on a container

Observed in session 2026-07-29:
- User wanted WhatsApp outbound messaging via Camofox
- Container lacked `libgtk-3.so.0` and blocked user-namespace sandboxing,
  so Camofox launch failed even after server came up
- No preinstalled Chrome, no sudo, no docker daemon access
- Playwright downloaded Chromium + Headless Shell with hundred-MB cdn fetch
- Chrome launched successfully under Xvfb with `--no-sandbox`
- `PLAYWRIGHT_BROWSERS_PATH` override avoids root-owned
  `/opt/hermes/.playwright` permission errors

Key UX note from user:
-"Do not narrate failed retries unless asked"
- "Do not repeat paths that were already rejected"
- Prefers direct fallback rather than long explanation

Implication for future browser-backends skill use:
- do not retry Camofox on constrained containers when Playwright CDP is available
- preserve user preference for concise, action-first troubleshooting
