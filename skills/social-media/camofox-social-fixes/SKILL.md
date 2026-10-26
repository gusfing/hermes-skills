---
name: camofox-social-fixes
description: |
  Session-tested fixes and pitfalls for Camofox-based social automation.
  Complements `x-social-poster` and `camofox-social-automation`.
  Use when posting to X/LinkedIn from Camofox and encountering health-probe
  restarts, viewport schema errors, or silent typing failures.
version: 0.1.0
tags: [camofox, x, linkedin, posting, playwright, workaround, automation]
---

# Camofox Social Fixes

## When to use

- Use after loading `x-social-poster` or `camofox-social-automation`.
- Use specifically when Camofox health probes trigger browser restarts,
  or when `/type` succeeds but X’s React composer remains empty/disabled.

## Verified fixes

### 1. Health-probe restart loop on `Browser.setDefaultViewport`

Symptom: Camofox restarts every ~60s with:
  ```
  Protocol error (Browser.setDefaultViewport):
  Found property "<root>.viewport.isMobile" - false which is not described in this scheme
  ```

Fix: patch `node_modules/camoufox/node_modules/playwright-core/lib/coreBundle.js`
around line 45563 — strip `isMobile` from the viewport object before sending to
the Camoufox juggler:

```javascript
const { isMobile, ...vpWithoutMobile } = viewport;
await this._browser.session.send("Browser.setDefaultViewport", {
  browserContextId: this._browserContextId,
  viewport: vpWithoutMobile
});
```

Pitfall: this is a compatibility mismatch between Playwright's CDP implementation
and Camoufox's custom juggler protocol — not a GTK/sandbox/env issue. Reinstalling
system libraries will not fix it.

### 1b. isMobile error at `newContext()` / `launchPersistentContext()` creation

Symptom: Same `isMobile: false` schema error, but at context creation time instead
of health probe. Affects `browser.newContext()` and `browser.launchPersistentContext()`.

Workaround A (preferred): use `browser.newContext({ viewport: null })` — passing
`viewport: null` avoids the CDP `setDefaultViewport` call entirely.

```javascript
const browser = await cf.Camoufox({ headless: true, os: 'linux', ... });
const context = await browser.newContext({ viewport: null });  // no isMobile error
const page = await context.newPage();
```

Workaround B: same playwright-core patch as fix #1.

Pitfall: `launchPersistentContext` with `data_dir` triggers the error because it
sets a default viewport (1280x720, isMobile:false) at creation time. Use `launch()`
+ `newContext({ viewport: null })` instead.

### 2. Keyboard `mode=keyboard` type may not update X React state

Symptom: `/tabs/{tabId}/type` returns `{"ok":true}` but:
- `data-testid="tweetTextarea_0"` remains empty
- Post button stays disabled

Do not treat `ok` as proof of typing success. Always verify with a follow-up
snapshot or `evaluate` of `innerText`/`textContent`.

### 3. DOM mutation usually does not reach X state

Symptom: setting `innerText`, `textContent`, or dispatching `input/change/keyup`
on `[data-testid="tweetTextarea_0"]` does not enable Post.

X’s composer expects real input/event flows; synthetic DOM edits are ignored by
React state in practice. Avoid DOM injection as the primary typing strategy.

## Preferred fallback hierarchy

1. Camofox keyboard-mode typing, verified by snapshot
2. Playwright/Chromium direct automation using exported session state
3. X v2 API with bearer token, if available

## Reusing an existing logged-in profile instead of importing cookies

If manual cookie import into a fresh `userId` lands on login/onboarding,
don’t keep retrying imports. Search the existing Camofox profile directory
for previously stored profiles and probe them directly:

- list `/opt/data/.camofox/profiles`
- for each profile hash, create a tab with `userId` set to your account id
  and `sessionKey` set to the profile hash
- snapshot `/compose/post` or `/home`; if it shows logged-in refs such as
  `Account menu`, `Post` link, or `textbox "Post text"`, stop—this profile
  already has a live X session
- reuse that exact `sessionKey` for future posts; do not recreate tabs with
  random session keys or expect old tab IDs to survive browser restarts

Pitfall: Camofox tab IDs become invalid after browser restart with `410 Gone`.
Session/profile identity lives in `sessionKey`/profile hash, not a single tab.

## Post-button may stay disabled because refs changed

`/type` often succeeds but leaves Post disabled. In that case:
- re-snapshot
- locate `textbox "Post text"` and `button "Post"` refs fresh
- do not reuse refs from a previous snapshot

If Post is still disabled after verified keyboard typing, do not loop;
switch to a different backend path.

## Playwright direct automation pattern

When Camofox composer typing is unreliable:
- launch Playwright Chromium with existing profile / storage state
- navigate to `https://x.com/compose/post`
- focus `[data-testid="tweetTextarea_0"]`
- type with `page.keyboard.type('hello world', { delay: 20 })`
- submit with `Control+Enter`
- verify:
  - new URL contains `/status/`
  - timeline contains the posted text

If Playwright lands on login/onboarding, the session has no usable X cookies;
export cookies/storage state from a browser where X is already logged in.

## Cookie-backed SSO caveat

Successful cookie import does not guarantee an active site session.
Always verify with page-state evidence:
- logged-in nav/account menu
- accessible feed/composer
- absence of login/onboarding UI

## LinkedIn cookie import via Camoufox

See `references/linkedin-cookie-import-camoufox.md` for the full verified workflow.

Summary: launch Camoufox, create context with `viewport: null` (to avoid isMobile
error), add all LinkedIn cookies via `context.addCookies()`, navigate to feed,
verify URL contains `/feed/` not `/login`. Save session cookies for reuse.

## Scripts

- `scripts/verify_camofox_health.sh` — probe Camofox and detect viewport-schema restarts
- `scripts/refresh_tab_refs.py` — snapshot textbox/Post refs for the active tab