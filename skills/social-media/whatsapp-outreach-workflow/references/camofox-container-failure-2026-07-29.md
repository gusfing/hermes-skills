# Session detail: Camofox launch failure, 2026-07-29

Environment facts
- Container runtime: Linux, no `sudo`, no system package manager access from this user
- Missing dependencies observed:
  - `libgtk-3.so.0`
  - sandbox namespace/unshare capability (`CanCreateUserNamespace() clone() failure: EPERM`)
- Camofox 1.13.0 installed locally at `/opt/data/node_modules/@askjo/camofox-browser`
- Playwright cache was empty in this session; `npx playwright install chromium` did not complete during investigation

Stable references
- Camofox server port default: `9377`
- Camofox profiles dir: `/opt/data/.camofox/profiles`
- Camofox cache dir: `/opt/data/.cache/camofox`

Lesson
Container launch failures here are environmental, not a Camofox or skill bug.
Do not treat this as an authoritative negative verdict on Camofox;
the user explicitly wants Camofox as the primary backend.
