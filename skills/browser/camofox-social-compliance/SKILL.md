---
name: camofox-social-compliance
description: |
  Reusable patterns for Camofox browser automation against social platforms.
  Covers X compose fragility, image upload workarounds, cookie normalization,
  VNC as fallback, and auth-health tracking. Use this skill when troubleshooting
  or building automation for X, LinkedIn, ChatGPT, WhatsApp, or similar sites
  through Camofox or Playwright-backed browser REST APIs.
version: 1.0.0
tags: [camofox, browser, social-media, automation, debugging]
---

# Camofox Social Compliance

Use this skill when:
- building social outreach/post automation with Camofox
- diagnosing login/upload/submit failures on X, LinkedIn, WhatsApp, ChatGPT
- normalizing cookie imports or session-reuse failures
- deciding between VNC interactive login and headless browser automation
- picking a fallback backend when Camofox stays broken

## Response style

User preference is direct and concise:
- lead with the blocker/fix, not diagnostic narration
- if blocked by auth, say `auth-required` and pivot once
- do not repeat paths that were already rejected
- only repeat failed setup paths if the user asks for the debug trail

## Cookie import rules

- Normalize `expires` to `int` or omit it entirely for session cookies.
- Do **not** send `expires: null`; this Camofox build rejects it.
- Ignore `__cf_bm` and other short-lived tracker cookies when deciding whether auth is valid.
- Watch `auth_token` for X, `li_at`/`li_rm` for LinkedIn.

## X composer patterns

### Composer open
- Accessibility ref clicks for `Post`/`compose/post` often stay on `/home`.
- Prefer JS `evaluate` over ref clicks to open the inline composer.
- Use both stable selectors and element visibility checks; keep a fallback snapshot path.

### Media upload
- Browser automation via refs is unreliable for image attachment.
- Use one of:
  - manual-complete handoff preserving the current `userId` + `tabId`
  - external real X API/media upload step
  - VNC interactive completion if VNC is available

## Working X posting method

**When the user supplies a posting/growth playbook**, or when scheduling
recurring posts on a timer, see `references/user-supplied-growth-specs.md` —
building the spec, enforcing its style rules as code, and which platform caps
to push back on rather than silently apply.

When Camofox DOM/click submit doesn’t enable the Post button, reliable alternative:
1. Accept Netscape cookie export from user’s desktop browser
2. Import into Playwright Chromium via `context.addCookies(cookies)`
3. Use `page.focus('[data-testid="tweetTextarea_0"]')` + `page.keyboard.type(text, { delay: 40 })`
4. Do **not** rely on Playwright `.click()` — overlay intercepts often fail silently
5. Submit via `page.evaluate(() => { const btn = document.querySelector('[data-testid="tweetButton"]') || document.querySelector('[data-testid="tweetButtonInline"]'); if (btn) btn.click(); })`
6. Successful post: URL redirects to `https://x.com/home`
7. When debugging, lookup: screenshot at failure point to confirm composer state

**A URL redirect is not confirmation** — the composer clears on a failed submit
too. Confirm by polling the profile feed; a post can be invisible at 6s and
visible at 39s. See `references/x-posting-and-community-targeting.md` for
community targeting, the reply-dialog `tweetTextarea_0` collision, and the
audience-label readback.

## WhatsApp Playwright fallback

When Hermes CDP tools time out on `web.whatsapp.com`, Playwright persistent context often still works:
1. Use existing Chrome profile:
   ```js
   const context = await chromium.launchPersistentContext('/opt/data/chrome-profiles/wa_account_a', {
     executablePath: '/opt/data/.playwright/chromium-1234/chrome-linux64/chrome',
     args: ['--no-sandbox','--disable-gpu'],
     headless: true,
     userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
   });
   ```
2. **Critical**: WhatsApp Web checks UA; override with a current Chrome UA string to avoid browser-compatibility error page
3. Pass profile path as `userDataDir` parameter, not as `--user-data-dir` in `args`
4. Navigate to `https://web.whatsapp.com`, wait for `domcontentloaded`, then inspect state:
   - QR: `await page.$('canvas')` → `.screenshot()`
   - chats: snapshot after `networkidle` or manual wait
5. Composer input selector fallbacks for chat:
   ```js
   '[contenteditable="true"][data-tab="10"]',
   '#main footer div[contenteditable="true"]',
   'div[spellcheck="true"]',
   'footer div[contenteditable="true"]'
   ```
6. Send: `input.type(text, { delay: 30 })` → `page.keyboard.press('Enter')` → verify chat history + cleared box

## Outreach dashboard pattern

Pattern: local HTTP dashboard at `/opt/data/outreach/dashboard/` for:
- Live QR image at `/public/qr.png`
- `/api/wa/start` returning 200 immediately; forks detached WhatsApp launch to a temp script file so server doesn’t block
- `/api/wa/status` returns `connected`, `hasQr`, `qrAgeSeconds`
- `/api/campaign/contacts` returning campaign JSON
- `/api/campaign/dry-run` for safe testing

Routing errors (502/503/tunnel unavailable) favor direct filename send/delivery over tunneled delivery.

## Reading absence on a social platform

A page that renders empty is the most expensive kind of wrong answer, because
nothing in the UI distinguishes "not there" from "I am looking at the wrong
surface" or "the render has not finished". Two false negatives in one session,
both caught by the user:

- An inbox that looked empty was sitting behind a passcode gate — the empty
  render was the recovery page, not the content.
- A post checked at 6s on one feed read as "did not publish". It was live at
  39s, visible on the profile feed, invisible on the community feed I checked.

Before reporting "it is not there":

1. **Re-check a different surface.** If the community feed is empty, look at
   the profile feed. Absence on one surface is not absence in general.
2. **Confirm no gate is in the way** — passcode, login, modal mask, or a
   permission wall renders as an empty panel.
3. **Re-read after a delay.** Async rendering is normal; one read is not a
   verdict. Poll a few times.
4. **Name the surface and the time** in the report: "not on the profile feed at
   40s" rather than "not posted".

If the only available evidence is an empty read, the honest output is
"not found where I looked", plus a statement of what was not checked.

## Failure posture

- classify failure as `click-noop`, `redirect-loop`, `auth-inactive`, `cdp-timeout`, or `media-upload-blocked`
- stop after one failure in breadcrumb state
- always capture a screenshot at failure point
- prefer manual handoff over blind retries

## Session hygiene

- reuse same `userId` + `sessionKey` across automation runs
- export storage state after interactive/VNC login for stronger persistence than raw cookie exports
- track auth-cookie expiry only, not tracker cookies
