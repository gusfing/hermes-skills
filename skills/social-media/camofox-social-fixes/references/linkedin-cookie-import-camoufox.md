# LinkedIn Cookie Import via Camoufox — Verified Workflow

## What works

Importing LinkedIn cookies directly into a Camoufox session and verifying login
by checking the feed page. This is an alternative to the manual-login pattern
documented in the parent skill.

## Cookie format

The Camoufox `context.addCookies()` method accepts an array of cookie objects:

```javascript
[
  { name: 'li_at', value: 'AQED...', domain: '.linkedin.com', path: '/', secure: true, httpOnly: true },
  { name: 'JSESSIONID', value: 'ajax:...', domain: '.linkedin.com', path: '/', secure: true, httpOnly: true },
  // ... all cookies from the browser
]
```

Each cookie needs at minimum: `name`, `value`, `domain`, `path`. `secure` and
`httpOnly` should match the original cookies (LinkedIn sets both to true for
auth cookies).

## Key LinkedIn cookies

- `li_at` — primary access token (required)
- `JSESSIONID` — session ID
- `lidc` — data center routing
- `bcookie`, `bscookie` — browser identification
- `li_rm`, `UserMatchHistory`, `AnalyticsSyncHistory` — tracking/analytics
- `g_state`, `_guid`, `aam_uuid` — Google/AAID tracking
- `dfpfpt`, `mbox`, `s_fid` — marketing/analytics

All cookies must be included for the session to work; LinkedIn validates
multiple cookies, not just `li_at`.

## Verified working flow

```javascript
const cf = require('camoufox');

const cookies = [ /* 20 LinkedIn cookies */ ];

const browser = await cf.Camoufox({
  headless: true,
  os: 'linux',
  locale: 'en-US',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});

// IMPORTANT: use newContext({ viewport: null }) to avoid isMobile bug
const context = await browser.newContext({ viewport: null });
const page = await context.newPage();

await context.addCookies(cookies);
await page.goto('https://www.linkedin.com/feed/', {
  waitUntil: 'domcontentloaded',
  timeout: 30000,
});
await page.waitForTimeout(5000);

// Verify: URL should NOT contain /login or /signin
const loggedIn = !page.url().includes('/login') && !page.url().includes('/signin');
```

Result: 24 cookies saved, feed page accessible, screenshot confirms login.

## Verification signals

- URL is `https://www.linkedin.com/feed/` (not `/login` or `/signin`)
- Page title is not "Sign in" / "Log in"
- Screenshot shows feed content (posts, sidebar)
- `context.cookies()` after session shows persisted cookies

## Save cookies for reuse

```javascript
const savedCookies = await context.cookies();
fs.writeFileSync('linkedin-cookies.json', JSON.stringify(savedCookies, null, 2));
```

Subsequent runs can load from this file and skip the initial import.

## Pitfalls

1. **Missing cookies**: importing only `li_at` is not enough — LinkedIn checks
   multiple cookies. Include all of them.
2. **Wrong domain**: cookies must use `.linkedin.com` (with leading dot) not
   `linkedin.com` or `www.linkedin.com`.
3. **No viewport null**: forgetting `viewport: null` in `newContext()` triggers
   the isMobile schema error (see parent skill fix #1b).
4. **Expired cookies**: LinkedIn tokens expire. If login fails, the cookies need
   refreshing (re-login in a real browser, re-export).
5. **Headless detection**: LinkedIn may show different content in headless mode.
   The feed page still loads but may show "Loading" — verify with URL check,
   not just visual inspection.

## References

- Parent skill: `camofox-social-fixes` (fix #1b — isMobile workaround)
- Parent skill: `camofox-social-automation` (manual-login fallback pattern)
