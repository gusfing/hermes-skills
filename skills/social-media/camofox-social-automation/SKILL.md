---
name: camofox-social-automation
description: |
  Verified patterns, blockers, and stop conditions for social platform
  automation via Camofox. Use alongside narrower platform skills such as
  x-social-poster or linkedin-outreach. Encodes session-tested composer
  behavior and fallback rules.
version: 1.0.0
tags: [camofox, social-media, x, linkedin, automation, post, outreach]
---

# Camofox Social Automation

This skill is a session-tested companion for platform-specific social
automation skills. It encodes patterns, failure modes, and fallback rules
observed in Camofox browser sessions.

## Trigger conditions

Use this skill when:
- social post automation via Camofox behaves differently than the naive ref-click flow
- media attach silently fails after composer interaction
- login state appears logged in but post composer does not enable
- deciding whether Camofox is worth further debugging vs. switching browser backends

Do not use this skill when another backend is already verified and task-fit. If local Chrome CDP is reachable and Camofox-specific anti-detect features are not required, prefer that backend and skip Camofox debugging.

## Backend selection

Rule for this environment:
- If the task requires anti-detect behavior, isolated identities, or login-state
  separation, **use Camofox**.
- If Camofox is unavailable or cannot complete a specific platform action after
  reasonable repair attempts, switching backends is allowed. For this user,
  prefer the fastest path that delivers results; retrying Camofox indefinitely
  is not required.
- For LinkedIn / X / Instagram outreach/automation, Camofox is the preferred
  backend here because account isolation matters. CDP fallback is acceptable
  when Camofox cannot complete the job.

## Composer open: JS first, refs second

Observed behavior on X/Camofox:
- direct navigation to `/compose/post` can redirect back to `/home` without opening the composer
- clicking `Post` nav ref from snapshot may keep the home view
- `Add photos or video` / `Choose File` ref clicks can reset navigation instead of attaching media

Preferred opener:
```js
const candidates = Array.from(document.querySelectorAll('[data-testid="tweetTextarea_0"], [href="/compose/post"], [data-testid="SideNav_NewTweet_Button"], a[href="/compose/post"]'));
const el = candidates.find(e => e.offsetParent !== null || e.tagName === 'A');
if (!el) return 'no_candidate';
el.click();
return 'clicked';
```

Immediately after any composer interaction:
- snapshot again
- check current URL
- do not continue blindly if you are back on `/home`

## Media attach: expect failure in Camofox

Observed:
- ref-based file input clicks reset navigation away from composer
- hidden-input JS injection is blocked by browser security
- paste of image data from automation context is unreliable

Rule:
- success = preview or attachment indicator
- once JS-open succeeds but attach does not, stop and switch fallback instead of retrying the same click

## Fallback order

1. **Use Camofox JS opener first**: if ref-click for composer redirects to `/home`, run the
   JS opener before changing backends.
2. **Use Camofox inline composer**: snapshot home after redirect; `textbox "Post text"`
   is usually present. Use `/type` with `mode: keyboard` there.
3. **Stop and report exact state**:
   - current URL
   - snapshot refs around composer controls
   - screenshot
4. **Manual complete in Camofox** if available:
   - user finishes upload/submit
   - automation resumes only if a new reliable control ref emerges
5. **Manual login for LinkedIn**: cookies alone may not be enough. Open Camofox
   LinkedIn login page, have the user log in manually once, then reuse that
   profile. See `references/linkedin-camofox-login-workaround.md`.
6. **Playwright cookie-backed session**:
   - When Camofox shows logged-in state but React keyboard submit still fails,
     use Playwright Chromium with exported X cookies (`auth_token`, `ct0`, etc.)
   - `page.goto('https://x.com/compose/post')` and then `page.focus('[data-testid="tweetTextarea_0"]')`
   - Type with `page.keyboard.type(...)`, dismiss overlays with `Escape`, then submit
   - This path is preferred over CDP here when X needs a real React input path
7. **Manual post**:
   - safest when Camofox clearly exposes composer but not attach
8. **Revisit automation later**:
   - after Camofox/server version changes or new verifiable attach method
9. **Fallback to Chrome CDP** when:
   - Camofox launches but **blocked by React/store-level state** after one retry, OR
   - Camofox cannot launch after reasonable repair attempts, AND
   - user explicitly approves switching backends

Known X submit caveats in automation:
- a DOM `data-testid="mask"` layers element can intercept pointer events on compose
- Ctrl/Enter submit should be attempted only after screenshot/snapshot confirms composer field is focused
- pseudo-submits via `KeyboardEvent('keydown', {key:'Enter', ctrlKey:true, ...})`
  from JS evaluation did not enable the Post button in observed sessions

## Stop conditions

Stop immediately and surface the degradation instead of retrying when:
- URL reverts to `/home` after composer interaction
- `Post` button remains disabled despite apparent composer state
- upload refs reset the page
- verification criteria are not met after submit

## Verification signals

After submit, look for:
- URL containing `/status/`
- success toast/notification
- timeline article for the new post
- screenshot evidence confirming publish state

## Cookie-backed SSO caveat

Successful cookie import does not guarantee active site login.
Observed: ChatGPT accepted cookies but still rendered login UI.
Always verify with page-state evidence, not HTTP status alone.

## LinkedIn cookie import — verified 2026-08-21 (escalated)

In this environment (Camofox v1.13.1, full Netscape cookie set with
`li_at`, `JSESSIONID`, `li_rm`, `bscookie`, etc.), **cookie import does NOT
result in a working LinkedIn session**. The earlier claim that it could was
incorrect — this session (same date) proved the opposite: after importing 24
cookies, pages render as "Problem loading page" with empty DOM, or
`NS_ERROR_REDIRECT_LOOP` on the homepage.

**Verified failure (2026-08-21):**
- Profile page (`/in/<profile>/`): title = "Problem loading page", zero buttons,
  zero text content, empty `body.innerText`
- Homepage (`/`): `NS_ERROR_REDIRECT_LOOP` — redirect loop at domain level

**Required cookie set (minimum):** `li_at` (auth token), `JSESSIONID`,
`bscookie`, `bcookie`, `li_sugr`, `li_rm`, `lidc`, `liap`, `lang`,
`g_state`, `_guid`, `aam_uuid`, `li_theme`, `li_theme_set`, `dfpfpt`,
`visit`, `s_fid`, `mbox`, `timezone`, `sdui_ver`. A full Netscape export
with all these cookies is more reliable than a minimal subset.

**Import procedure:**
1. Export cookies from a working LinkedIn browser session (Netscape format)
2. `POST /sessions/{userId}/cookies` with body `{ "cookies": [...] }`
3. Create a new tab with `https://www.linkedin.com/` as initial URL
4. Navigate to target URL (`/feed/`, `/in/`, etc.)
5. **Verify with page-state evidence, NOT HTTP status or import success**
   — LinkedIn can return 200 on a blocked page. Check:
   - `document.title` is not "Problem loading page"
   - `document.body.innerText` is not empty
   - Buttons exist on the page (not `[]`)
   - URL does not contain `/login` or `/signin`

When cookie import still fails: If pages render as "Problem loading page"
or redirect loops, the server-side session is invalidated (IP change,
fingerprint mismatch, `li_at` expiry, or LinkedIn anti-bot blocking — see
`references/linkedin-anti-bot-blocking-2026-08-21.md`). Fall back to
the manual-login-then-reuse-profile pattern.

## LinkedIn anti-bot blocking — verified 2026-08-21 (escalated)

LinkedIn's anti-bot detection blocks automated browser fingerprints regardless
of cookie state. The blocking has escalated to multiple levels simultaneously —
network drops, redirect loops, empty-DOM rendering, AND IP-level API blocking.

**Escalation timeline (this environment):**

1. **2026-08-21 (initial):** Page-level blocking — profile pages returned "Problem loading page" with empty DOM. Homepage still loaded.
2. **2026-08-21 (later):** Domain-level escalation — homepage started returning `NS_ERROR_REDIRECT_LOOP`. Feed endpoint returned `NS_ERROR_NET_EMPTY_RESPONSE`.
3. **2026-08-31 (CLI tools):** IP-level blocking confirmed — direct HTTP requests to LinkedIn Voyager API from this Oracle Cloud IP return empty responses. Public pages return HTTP 999 (LinkedIn's bot-block code). Even valid `li_at` + `JSESSIONID` cookies don't help because the server invalidates sessions from flagged IPs.

**Anti-bot layers (all observed):**

| Layer | Symptom | Tools affected |
|---|---|---|
| Browser fingerprint | "Problem loading page", empty DOM, zero buttons | Camofox (Firefox headless), Chrome CDP, Playwright |
| Redirect loop | `NS_ERROR_REDIRECT_LOOP`, `ERR_TOO_MANY_REDIRECTS` | Camofox, Chrome, Playwright |
| Network drop | `NS_ERROR_NET_EMPTY_RESPONSE`, empty API response | Camofox feed endpoint, all CLI HTTP tools |
| IP reputation | HTTP 999 on public pages, 302 session invalidation, empty Voyager API | All tools from this Oracle Cloud IP |

**What was tested and blocked:**

| Backend | Symptom | Pages affected |
|---|---|---|
| Camofox Firefox (headless) | Homepage: `NS_ERROR_REDIRECT_LOOP`. Profile: "Problem loading page" — empty DOM (zero buttons, zero text, empty `body.innerText`), page title = "Problem loading page" | `/`, `/in/<profile>/` |
| Chrome CDP (headless) | Profile locked by remote process or `ERR_TOO_MANY_REDIRECTS` / `ERR_HTTP_RESPONSE_CODE_FAILURE` | `/`, `/feed/`, `/in/<profile>/` |
| Playwright Chromium (headless) | `ERR_TOO_MANY_REDIRECTS` on homepage | `/`, `/feed/` |
| `@bcharleson/linkedincli` (HTTP CLI) | Auth accepted, all API calls return empty (15s timeout, no output) | Voyager API endpoints |
| `lxgicstudios/linkedin-cli` (HTTP CLI) | Auth saves OK, calls fail with `fetch failed` | Voyager API endpoints |
| Direct curl (Oracle Cloud IP) | Homepage HTTP 200, Voyager API empty, public pages HTTP 999 | All LinkedIn endpoints |

**Verification method (page-state, NOT HTTP status):**

For browser automation:
- `document.title` — if "Problem loading page", blocked
- `document.body.innerText` — if empty, blocked
- `document.querySelectorAll("button")` — if `[]`, no interactive elements
- URL — if `/login` or `/signin`, not authenticated
- HTTP 200 alone does NOT confirm a working session

For CLI tools:
- `linkedin status` returning `logged_in:true` does NOT mean API calls work
- Every API call must return actual data, not empty/timeout
- Direct curl to Voyager API is the definitive test — if curl fails, no CLI tool will work from this IP

**What does NOT work (do not retry):**

- Cookie import alone (any browser backend, any cookie set) — produces blocked/empty pages, NOT working sessions
- Multiple retries of the same blocked approach
- Headless Chrome/Playwright/Chromium against LinkedIn
- Clicking "Try Again" on "Problem loading page" — does not break the loop
- HTTP-based LinkedIn CLI tools from a flagged IP — auth works locally but all API calls fail
- Installing multiple LinkedIn CLI tools without resolving binary name conflicts (both `@bcharleson/linkedincli` and `@linkedapi/linkedin-cli` claim the `linkedin` binary)

**What works:**

- **Option A**: Manual login in Camofox (visible browser, not headless), then reuse the `userId`/`sessionKey` profile. This is the only verified working approach in this environment — BUT requires a display (Xvfb/VNC) and the Oracle Cloud IP may still block even manual sessions.
- **Option B**: LinkedIn Official API (requires Developer account, OAuth, approval)
- **Option C**: Route through a non-blocked IP (different cloud provider, proxy, or another VPS not on Oracle Cloud)
- **Option D**: `@linkedapi/linkedin-cli` — routes through their proxy server with a different exit IP. Untested — might bypass IP-level blocking. Install conflict with `@bcharleson/linkedincli` must be resolved first (rename binary).

**LinkedIn CLI tools — detailed findings:**

See `references/linkedin-cli-tools-2026-08-31.md` for:
- Tool-by-tool install commands and feature comparison
- Config file paths and field name pitfalls (`jsessionid` vs `JSESSIONID`)
- Binary name conflict between `@bcharleson/linkedincli` and `@linkedapi/linkedin-cli`
- Direct curl test results confirming IP-level blocking

## Container launch status (2026-07-30)

Inside this container, GTK3 and browser runtime deps have been installed:
`libgtk-3-0t64`, `libdbus-glib-1-2`, `libx11-xcb1`, `libxtst6`, `libxss1`,
`libasound2t64`, `libnss3`, `libxcb-dri3-0`, `libdrm2`, `libgbm1`,
`libxcomposite1`, `libxdamage1`, `libxi6`, `libcups2t64`, `libatk1.0-0t64`,
`libatk-bridge2.0-0t64`, `libpango-1.0-0`, `libcairo2`, `libxrandr2`,
`libatspi2.0-0t64`, `xvfb`.

After these installs, the Camoufox binary launches successfully under Xvfb.

### Known Playwright wrapper issue

The wrapper's health probe crashes on this Camoufox build with:

```
Protocol error (Browser.setDefaultViewport)
Found property "<root>.viewport.isMobile" - false which is not described in this scheme
```

Without a local patch, this triggers repeated `browser_restart:health probe failed`
loops even though the browser is healthy.

### Verified local patch

In `node_modules/@askjo/camofox-browser/server.js`, locate the health probe and
change the catch block to suppress restart for the viewport schema mismatch, e.g.:

```js
if (/setDefaultViewport|isMobile/.test(msg)) {
  log('info', 'health probe suppressed for Camoufox viewport schema mismatch', { timeSinceSuccessMs });
} else {
  restartBrowser('health probe failed').catch(() => {});
}
```

With this patch, Camofox stays up and tab create/navigate/snapshot/click/type work.

## REST client URL bug — verified 2026-08-21

**Symptom:** All Camofox REST API calls fail with errors like
`"userId required"` or `"Cannot read properties of undefined"`.

**Root cause:** The HTTP helper function in automation scripts uses
`url.pathname` which strips query parameters. Camofox's `/snapshot` and
other endpoints require `userId` as a query parameter.

**Fix:** Change `path: url.pathname` to `path: url.href` in the `request()`
helper function. See `references/camofox-rest-client-url-pathname-bug.md`.

**Scope:** Any Node.js script using `new URL(base + path)` then passing
`url.pathname` to `http.request()` options. This affected three LinkedIn
automation scripts (`linkedin_message.js`, `linkedin_campaign.js`,
`post_linkedin.js`) in this session.

## Playwright pseudo-selectors do not work in Firefox

Camofox uses Firefox, not Chromium. Playwright-specific pseudo-selectors are NOT valid CSS selectors and will throw `invalid_selector` errors from `document.querySelector()`:

- `:has-text("...")` — Playwright-specific, not real CSS
- `:contains("...")` — Playwright-specific, not real CSS
- `:contains-placeholder("...")` — Playwright-specific, not real CSS

**Symptom:** `page.evaluate: Document.querySelector: '.artdeco-button--primary:has-text("Connect")' is not a valid selector`

**Fix:** Never use these pseudo-selectors in `evaluate()` expressions or `document.querySelector()` calls. Instead, query elements by standard CSS selectors and filter by text content in JavaScript:

```javascript
// WRONG — throws invalid_selector:
document.querySelector('.artdeco-button--primary:has-text("Connect")')

// RIGHT — query all buttons, filter by innerText:
(() => {
  const buttons = document.querySelectorAll('button');
  for (const btn of buttons) {
    const text = (btn.innerText || btn.textContent || '').trim();
    if (text === 'Connect' && btn.offsetParent !== null && !btn.disabled) {
      return btn;
    }
  }
  return null;
})()
```

**Scope:** Any Node.js script calling `evaluate()` with `document.querySelector()` using Playwright pseudo-selectors. This affected `linkedin_message.js` (Connect/Send buttons, note textarea) and would affect any Camofox automation script targeting LinkedIn, X, or any site where the author defaulted to Playwright selector syntax.

**Verification:** After fixing, run `node --check script.js` and confirm the selector strings no longer contain `:has-text`, `:contains`, or `:contains-placeholder`.

## Composer behavior on X/Camofox

Observed behavior on X:
- Direct navigation to `/compose/post` can redirect back to `/home` without opening composer
- clicking `Post` nav ref from snapshot may keep the home view
- `Add photos or video` / `Choose File` ref clicks can reset navigation instead of attaching media
- After ref-based type into inline composer with wrong ref, `Post` can stay disabled
- JS injection of `textContent`/`innerText`/`value` updates the DOM but **does not sync React state**, so Post can remain disabled
- Keyboard events injected via `KeyboardEvent('keydown', {key:'Enter', ctrlKey:true, ...})` also did not enable the submit button in observed sessions
- Camofox `/tabs/{tabId}/type` with `mode: keyboard` + `pressEnter: true` did not complete a post from the inline composer in observed sessions
- X's React store does not recognize synthetic mutations from outside; you can see typed text in the DOM while the internal state stays empty, leaving the Post button disabled

**Stop rule:** if the inline composer shows typed text but the Post button is
still disabled, one retry is allowed after a fresh snapshot and a direct
type attempt. If it still fails, stop Camofox posting for that account and
surface the state. Do not keep retrying synthetic mutations; they will not
reach X's React store.

See `references/x-composer-camofox-debug-2026-07-30.md` for the exact failure
symptom and confirmed non-fix list.

Verified real pattern:
1. Snapshot home after redirect — inline composer `textbox "Post text"` is usually present
2. Use Camofox `/tabs/{tabId}/type` against that textbox ref
3. If Post button remains disabled, do NOT keep injecting fake DOM/events
4. Pivot to a backend with real input path trust; synthetic mutations alone won't reach X's store

Verified formula that works:
1. Snapshot home after redirect — inline composer `textbox "Post text"` is usually present
2. Use Camofox `/tabs/{tabId}/type` against that textbox ref
3. If Post button remains disabled, snapshot again and verify whether input is actually registered by React
4. If disabled, stop retrying text injection — it won't trigger React state, and further retries will only miss again

### Verified opener pattern

Run the JS opener first; only snapshot after it:
```js
const candidates = Array.from(document.querySelectorAll('[data-testid="tweetTextarea_0"], [data-testid="SideNav_NewTweet_Button"], a[href="/compose/post"]'));
const el = candidates.find(e => e.offsetParent !== null || e.tagName === 'A');
if (!el) return 'no_candidate';
el.click();
return 'clicked';
```

After JS opener:
- snapshot again
- check current URL
- if back on `/home`, still inspect: X often keeps an inline composer visible on home
- inline composer ref is usually `textbox "Post text"`
- do not continue blindly if the page unexpectedly bailed

## Messaging fallbacks

1. **JS opener first**
2. **Snapshot-ref composer**: inline `textbox` ref after home redirect
3. **Ref-click direct compose**: only if snapshot shows it clearly available
4. **Stop and report**: if composer opens but never enables

## Stop conditions

Stop immediately and surface the degradation instead of retrying when:
- URL reverts to `/home` after composer interaction
- `Post` button remains disabled despite apparent composer state
- upload refs reset the page
- verification criteria are not met after submit

## Companion skills

- `x-social-poster`: X/Twitter posting task entrypoint
- `browser-backends`: Camofox setup, cookie import, and multi-account isolation
- `whatsapp-web-outreach`: WhatsApp messaging automation patterns

## scripts

- `scripts/x_compose_verify.js` - minimal Camofox helper probe for current composer refs and URL after JS-open attempt
- `scripts/x-playwright-cookie-post-2026-07-30.md` - Playwright cookie-backed X posting workaround when Camofox React input fails

## references

- `references/x-composer-camofox-debug-2026-07-30.md` -- error transcript and stop condition for React state mismatch during X posting from Camofox
- `references/camofox-container-launch-fix-2026-07-30.md` -- concrete apt-get install command, health-probe workaround, and verified launch state for Camofox inside Docker/LXC containers
- `references/camofox-container-launch-failure-2026-07-29.md` -- earlier failure modes and why fresh Camofox install alone does not resolve them
- `references/linkedin-camofox-login-workaround.md` -- why Netscape cookie import alone often fails for LinkedIn, and the recommended manual-login-then-reuse-profile pattern
- `references/open-source-social-automation-options-2025.md` -- concise review of X/LinkedIn/Instagram automation alternatives and why isolated browser profiles are preferred in this environment
- `references/linkedin-cookie-import-verified-2026-08-21.md` -- session transcript: verified cookie import works in this environment
- `references/linkedin-anti-bot-blocking-2026-08-21.md` -- full test transcript: all automated browser approaches blocked by LinkedIn
- `references/camofox-rest-client-url-pathname-bug.md` -- root cause and fix for the url.pathname query-param stripping bug