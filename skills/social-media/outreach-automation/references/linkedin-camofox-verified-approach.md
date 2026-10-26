# LinkedIn Camofox: Verified Approach and Known Blockers

## Status

**As of 2026-08-21: LinkedIn automation via Camofox headless Firefox is BLOCKED.** All three browser automation approaches tested (Camofox Firefox, Chrome CDP, Playwright Chromium) were rejected by LinkedIn's anti-bot. Cookie import alone does not bypass the block.

This document captures the technical details that DO work (browser launch, context creation, URL scheme, composer interaction patterns) alongside the hard blockers (cookie import, headless browsing, anti-bot detection).

## Browser launch (tech details — these work)

### Camofox Firefox launch pattern

```js
const browser = await cf.Camoufox({
  headless: true,
  os: 'linux',
  locale: 'en-US',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
  // NO data_dir — do NOT use launchPersistentContext()
});

const context = await browser.newContext({ viewport: null });
const page = await context.newPage();
```

**Why these matter:**
- `browser.launch()` returns a Browser (not BrowserContext), avoiding the viewport bug
- `newContext({ viewport: null })` skips the CDP `setDefaultViewport` call that triggers the `isMobile` schema error
- `launchPersistentContext()` with `data_dir` triggers the error at context creation — avoid

### URL scheme restriction

Camofox blocks `about:blank` and any non-HTTP(S) URL when creating tabs. Always use a valid HTTPS URL:

```js
// WRONG — blocked:
await createTab('about:blank');

// CORRECT — use LinkedIn homepage:
await createTab('https://www.linkedin.com/');
```

If your script has a default `createTab()` parameter, set it to `'https://www.linkedin.com/'` not `'about:blank'`.

## What does NOT work for LinkedIn

### Cookie import (REST API or context.addCookies())

LinkedIn's server-side session validation fails regardless of cookie count. The REST API accepts cookies and returns `{"ok":true,"count":N}` but the browser context does not become authenticated. LinkedIn validates beyond cookie values — browser fingerprint, IP, and behavioral signals all factor in.

Tested with 24 cookies (including `li_at`, `JSESSIONID`, `PLAY_SESSION`, `AMCV`) imported via `POST /sessions/linkedin_main/cookies`. Import returned success but LinkedIn showed login page after navigation.

### Headless browsing + cookie import

Any headless browser (Camofox Firefox, Chrome CDP, Playwright Chromium) with cookie import is blocked by LinkedIn's anti-bot. Different symptoms depending on endpoint:

- **Feed (`/feed/`)**: `NS_ERROR_NET_EMPTY_RESPONSE` — network-level connection drop
- **Profile (`/in/<profile>/`)**: "The page isn't redirecting properly" — Firefox redirect loop detection
- **Homepage (`/`)**: Loads but redirects to `hp` (logged-out state)

### Multiple retries

The block is deterministic for the browser profile. Retrying the same approach yields the same result.

## Post composer flow (requires manual login first)

These patterns work **only after** a manually authenticated Camofox session:

1. Navigate to `https://www.linkedin.com/feed/`
2. Open composer via JS injection (multiple selector strategies)
3. Type text via JS injection into contenteditable or textarea
4. Click Post button via JS injection
5. Verify: check URL is not `/login`, take screenshot

Key insight: LinkedIn's React composer does NOT respond to CDP type/press commands reliably. JS evaluation with `document.execCommand('selectAll')` + `textContent`/`value` assignment + `input`/`change` event dispatch is more reliable.

## Messaging / connection requests (requires manual login first)

Same pattern: navigate to profile URL → JS-click Connect/Message button → JS-type note/message → JS-click Send.

**Important — button selectors:** Playwright pseudo-selectors (`:has-text()`, `:contains()`) do NOT work in Camofox Firefox's evaluate endpoint. Use standard `querySelectorAll` + text content matching:

```javascript
// BROKEN (Playwright pseudo-selectors):
'.artdeco-button--primary:has-text("Connect")'
'button:contains("Connect")'

// WORKING (standard DOM + text matching):
const buttons = document.querySelectorAll('button');
for (const btn of buttons) {
  const text = (btn.innerText || btn.textContent || '').trim();
  if (text === 'Connect' && btn.offsetParent !== null && !btn.disabled) {
    btn.click();
    return { clicked: true };
  }
}
```

## Verification

- URL must not contain `/login` or `/signin`
- Screenshot as proof
- For posts: check feed page is accessible after submit

## Script debugging checklist

Before running a LinkedIn automation script, verify:

1. **`node --check script.js`** — syntax check passes
2. **No null bytes** — `python3 -c "print(open('script.js','rb').read().count(b'\x00'))"` returns 0
3. **`log()` defined** — grep for `function log` returns exactly one match
4. **No Playwright pseudo-selectors** — grep for `:has-text(` and `:contains(` returns no matches in evaluate JS blocks
5. **Snapshot returns full response** — `snapshot()` returns `res`, not `res.snapshot`
6. **Cookie import in main flow** — `importCookies()` called before `createTab()` in the main execution path
7. **Default tab URL is `https://www.linkedin.com/`** — not `about:blank`

## Files built this session

- `scripts/post_linkedin.js` — standalone post composer
- `scripts/linkedin_message.js` — messaging + connection requests + search+connect
- `scripts/linkedin_templates.js` — 10+ template variants (connection, message, post)
- `scripts/linkedin_campaign.js` — campaign engine with JSON config, rate limiting, history
