---
name: whatsapp-outreach-workflow
description: |
  User-facing WhatsApp outreach workflow for multi-account outreach.
  Encodes user preferences: concise troubleshooting, no unsolicited cold blasts.
version: 1.1.0
tags: [whatsapp, outreach, messaging, playwrite, multi-account]
---

# WhatsApp Outbound Messaging Workflow

Use this skill when the user asks for:
- send WhatsApp outreach messages
- run WhatsApp follow-up sequences
- prospecting/messaging automation through WhatsApp
- dashboard with QR and campaign status

## Backend selection

**Primary:** Local Chrome CDP at `127.0.0.1:9222` with a dedicated profile dir.
**Fallback:** Playwright persistent context against the existing Chrome WhatsApp profile directory.

Justification:
- In containerized environments, Chrome CDP often reaches `Target.getTargets` but page snapshots/vision/click time out on WhatsApp.
- Playwright persistent-context with a real Chrome UA string overcomes WhatsApp Web UA rejection and preserves login state.
- Use Camofox only if Playwright/cdp paths are unavailable.

## Account model

- `wa_account_a`, `wa_account_b`, etc.
- Each account gets its own directory under `/opt/data/chrome-profiles/<account>`.
- Prefer persistent sessions: reuse same profile dir to preserve chat history.
- Do NOT reimport cookies repeatedly; only when login expires.

## Pre-flight checks

1. Check whether WhatsApp Web target exists in CDP.
2. If CDP page commands time out, report once and switch backend.
3. Try Playwright persistent-context with UA override before retrying CDP.

## Playwright WhatsApp session

- Launch with `chromium.launchPersistentContext(profileDir, { executablePath, args: ['--no-sandbox','--disable-gpu'], headless: true, userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36' })`.
- Navigate to `https://web.whatsapp.com`.
- Treat loading screen, QR login page, and logged-in chat list as three distinct states; verify before acting.

## Contact resolution

- Prefer contact list snapshots + known refs
- If contact not in list, use `https://wa.me/<number>` links or new-chat UI
- Always confirm contact identity from visible chat header before sending

## Messaging rules

- Confirm contact identity before sending
- Use the message box ref from the latest snapshot
- Send with Enter
- Verify: message appears in history, input box is cleared
- Add delays between sends (>= 3 seconds minimum)

## Dashboard

- Host on an isolated port, e.g. 3001, separate from other services.
- Provide endpoints for QR capture, status refresh, contacts list, and dry-run.
- `/api/wa/start` must return immediately; launch WhatsApp capture in a detached child process.
- Capture QR via `canvas` screenshot on `https://web.whatsapp.com`.

## Safety rules

- No bulk unsolicited messages in tight loops
- No retries without surfacing the exact failure
- Log sent/response status per contact
- If composer refs reset the page, stop and report

## Related skills and docs

- Composer behavior and fallback patterns: `browser-social-composer`
- X/Twitter posting: `x-social-poster`
- X verified publish path: `browser-social-composer`

## Troubleshooting caveats

- Cookie-backed SSO may succeed but leave the site in a logged-out UI.
  Always verify with page-state evidence, not HTTP status alone.
- WhatsApp Web rejects default Playwright/HeadlessChrome UA; always set a real Chrome UA.
- CDP reachability does not guarantee command success. One timeout per page surface is enough to trigger backend switch.
- Loading screens, QR codes, and logged-in state are distinct; do not loop between them unchanged.