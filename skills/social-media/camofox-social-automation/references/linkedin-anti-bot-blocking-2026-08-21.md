# LinkedIn Anti-Bot Blocking — Updated Findings (2026-08-21 through 2026-09-01)

## Status
**Verified non-working as of 2026-09-01 for most endpoints.** All three major browser automation approaches were tested and blocked. Cookie import alone does not bypass the block. **Blocking is selective by endpoint** — `identity/me` Voyager endpoint can work intermittently from this Oracle Cloud IP with fresh cookies, while `feed`, `search`, `connections`, and profile view of others are consistently blocked.

## What was tested (through 2026-09-01)

### 1. Camofox Firefox (headless) — 2026-08-21
- LinkedIn homepage — loads, later escalated to `NS_ERROR_REDIRECT_LOOP`
- LinkedIn feed — `NS_ERROR_NET_EMPTY_RESPONSE`
- LinkedIn profile pages — "Problem loading page" with empty DOM
- Cookie import via REST API — accepted 24 cookies, but LinkedIn shows login/empty page

### 2. Chrome CDP / Playwright Chromium (headless) — 2026-08-21
- Both blocked: `ERR_TOO_MANY_REDIRECTS`, `ERR_HTTP_RESPONSE_CODE_FAILURE`

### 3. HTTP CLI tools — 2026-08-31
- `@bcharleson/linkedincli`: auth accepted, all API calls return empty
- `lxgicstudios/linkedin-cli`: auth saves OK, calls fail with `fetch failed`
- Direct curl from Oracle Cloud IP: Voyager API empty, public pages HTTP 999

### 4. `@lucasygu/lockedout` (Patchright + real Chromium) — 2026-09-01
- `lockedout doctor`: clean (Node 22, Patchright 1.62.2, Chromium cached)
- Headless cookie-seed test: Chromium launches, 29 cookies inject successfully, LinkedIn homepage loads — but serves 39-byte blank page (fingerprint still detected)
- `lockedout` needs real Chromium profile from `lockedout login` — cookies file alone is not enough

### 5. `@bcharleson/linkedincli` with fresh cookies — 2026-09-01
- Fresh 29-cookie set imported
- `linkedin profile me` returned real profile data **once** (Kunal's profile: plainId `926091191`, publicIdentifier `kunal-sharma-webdev`)
- Subsequent `profile me` calls timed out
- `search`, `feed`, `connections` consistently timeout/302

## Selective IP-level blocking (new finding 2026-09-01)

LinkedIn's blocking from this Oracle Cloud IP is **endpoint-selective**, not uniformly blocked:

| Endpoint | Status from Oracle Cloud IP |
|---|---|
| `identity/me` (profile me) | **Intermittently works** — returned real data once with fresh cookies |
| `feed` | Consistently 302/empty |
| `search` | Consistently timeout/302 |
| `connections` | Consistently timeout/302 |
| Profile view of others | Consistently timeout/302 |
| Public pages (no cookies) | HTTP 999 (bot-block) |
| Homepage (no cookies) | HTTP 200 |

This means **no browser automation and no HTTP CLI tool will reliably work from a flagged cloud IP**, but `profile me` is a narrow exception that can work occasionally.

## Three distinct failure symptoms (all observed 2026-08-21)

1. **`NS_ERROR_NET_EMPTY_RESPONSE`** — network-level connection drop on `/feed/` and `/in/<profile>/`
2. **`NS_ERROR_REDIRECT_LOOP`** — Firefox redirect loop detection on homepage
3. **"Problem loading page" with empty DOM** — profile pages render Firefox error page with no LinkedIn UI

Plus (2026-09-01, HTTP CLI):
4. **Timeout** — requests hang until timeout (search, feed, connections from CLI tools)
5. **HTTP 302 redirect** — session invalidated server-side
6. **HTTP 999** — LinkedIn's bot-block response code on public pages

## Root cause

LinkedIn's anti-bot detection blocks automated browser fingerprints AND flagged cloud IPs regardless of cookie state. The blocking happens at the network/HTTP level (empty responses, redirect loops, response code failures, timeouts), not at the login page level. Cookies imported via any mechanism do not bypass this because LinkedIn validates server-side session state beyond cookie values — IP, browser fingerprint, JavaScript execution environment, and behavioral signals all factor in.

## Cookie import — actual behavior

- REST API / CLI tools accept the cookie payload and return success
- Cookies are stored in the browser context / local config
- After navigation or API call, LinkedIn still renders the login/consent page, empty DOM, or returns empty API response
- The `li_at` token alone is insufficient — server-side session validation fails for automated browser profiles AND flagged IPs
- **Fresh cookies matter**: the 2026-09-01 cookie set (29 cookies, freshly exported) allowed `profile me` to work once, while older cookies did not

## What actually works for LinkedIn automation

### Option A: Manual login in Camofox, then reuse profile
1. Launch Camofox with a visible browser (not headless)
2. Navigate to LinkedIn and log in manually (user performs the login)
3. Reuse the same `userId`/`sessionKey` for subsequent automation
4. The manual login establishes a server-side session that persists

This is the only verified working approach. It requires user participation for the initial login. After that, automation scripts can operate against the logged-in profile. **Caveat:** the Oracle Cloud IP may still block even manual sessions — unverified.

### Option B: LinkedIn Official API
- Requires LinkedIn Developer account, OAuth app, and approval
- More reliable but takes days to set up
- Rate limits and scope restrictions apply
- Not tested in this environment

### Option C: Route through a non-blocked IP
- Different cloud provider, residential proxy, or another VPS not on Oracle Cloud
- `@linkedapi/linkedin-cli` routes through their proxy — different exit IP, might bypass. Untested.
- Tailscale exit node from a non-cloud host might work

### Option D: `@lucasygu/lockedout` with manually logged-in Chromium profile
- On a non-blocked machine, run `lockedout login` to create a Chromium profile via manual LinkedIn login
- Then use `lockedout profile <username>` headlessly
- The Chromium profile carries the real browser fingerprint and server-side session

## What does NOT work (do not retry)

| Approach | Result | Do not retry |
|---|---|---|
| Camofox headless + cookie import | Blocked on `/feed/` | Yes |
| Chrome CDP headless + cookies | Profile locked / blocked | Yes |
| Playwright Chromium headless + cookies | Blocked on homepage | Yes |
| Cookie import alone (any browser) | Login page after navigation | Yes |
| Multiple retries of same approach | Same block | Yes |
| HTTP CLI tools from Oracle Cloud IP for feed/search/connections | 302/timeout | Yes |
| `lockedout` cookie file alone (no Chromium profile) | No session | Yes |
| Headless Chromium (Patchright) with injected cookies | 39-byte blank page | Yes |

## Decision tree for LinkedIn automation

```
Need LinkedIn automation?
├── Can user manually log in to Camofox/lockedout once?
│   └── YES → Manual login, reuse profile, then run scripts
├── Is there a non-blocked IP available?
│   └── YES → Route requests through it (proxy, different VPS, @linkedapi proxy)
├── Is LinkedIn API access available?
│   └── YES → Use official API
└── NO to all
    └── LinkedIn automation is NOT currently possible from this setup
        → Focus on working channels (WhatsApp, X, etc.)
```

## Escalation warning

The blocking escalated during a single session — homepage went from "loads" to `NS_ERROR_REDIRECT_LOOP`. LinkedIn's anti-bot can tighten over time. **Endpoint-selective blocking also means partial success is possible** — `profile me` worked once while other endpoints failed. Do not conclude "nothing works" from a single failed endpoint test.

## Cookie sharing workflow (2026-09-01)

When a user shares LinkedIn cookies by pasting the Netscape cookie string:
1. Parse the cookie string into structured objects (name, value, domain, path, secure, httpOnly, sameSite)
2. Write to both `~/.lockedin-cli/config.json` (for `@bcharleson/linkedincli`) AND `~/.lockedout/cookies.json` (for `@lucasygu/lockedout`)
3. **Critical:** use `sameSite: "None"` (capital N) for Patchright compatibility — lowercase `"none"` causes `context.addCookies()` to reject
4. Verify with `linkedin status` and `linkedin profile me`
5. Full cookie set should include at minimum: `li_at`, `JSESSIONID`, `bscookie`, `bcookie`, `li_sugr`, `li_rm`, `lidc`, `liap`, `lang`, `g_state`, `_guid`, `aam_uuid`, `li_theme`, `li_theme_set`, `dfpfpt`, `visit`, `s_fid`, `mbox`, `timezone`, `sdui_ver`

## Related

- `references/linkedin-cli-tools-2026-08-31.md` — tool-by-tool install commands, config paths, lockedout details, cookie-sharing workflow
- `references/linkedin-camofox-login-workaround.md` — manual-login fallback recommendation
- `references/camofox-rest-client-url-pathname-bug.md` — REST client bug (separate issue)
