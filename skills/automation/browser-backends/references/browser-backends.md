# Browser backends — notes from setup work

## Missing-Codex detection
- Component hierarchy matters: Hermes browser tools can use local browser tooling plus a separate Camofox server. A successful install/path check for `@askjo/camofox-browser` does **not** mean the wrapped Camoufox binary will launch. The health/availability checks can still fail.

## Linux dependency signature
- `libgtk-3.so.0: cannot open shared object file: No such file or directory`
- `Sandbox: CanCreateUserNamespace() clone() failure: EPERM`

## Preference order to recommend after seeing the above on Linux
1. Docker Camofox: `docker run -d -p 9377:9377 -e CAMOFOX_PORT=9377 jo-inc/camofox-browser`
2. Local Camofox only if the user can install system packages/runtime deps themselves:
   - `libgtk-3-0`, `libdbus-glib-1-2`, `libx11-xcb1`, `libxtst6`, `libxss1`, `libasound2`, `libnss3`, `libxcb-dri3-0`, `libdrm2`, `libgbm1`, `libxcomposite1`, `libxdamage1`, `libxi6`, `libcups2`, `libatk1.0-0`, `libatk-bridge2.0-0`, `libpango1.0-0`, `libcairo2`, `libxrandr2`, `libatspi2.0-0`, `xvfb`
   - Then retry Camofox server and validate `CAMOFOX_URL=http://localhost:9377`.

## User-facing `.env` pattern
```bash
export CAMOFOX_URL=http://localhost:9377
export CAMOFOX_REWRITE_LOOPBACK_URLS=true   # especially for Docker
```
