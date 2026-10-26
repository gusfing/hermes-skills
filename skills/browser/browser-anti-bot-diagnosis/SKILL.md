---
name: browser-anti-bot-diagnosis
description: >
  Diagnose headless browser blocks: anti-bot vs script bug.
---

# Browser Anti-Bot Diagnosis

When a headless browser (Camoufox, Playwright, Puppeteer, etc.) loads a URL
but the page is empty, stuck in a redirect loop, or shows "problem loading page"
— the first question is **is this a script bug or is the site blocking the
browser?** This skill captures the isolation methodology.

## The 4-Step Isolation Test

Run these in order. Each step eliminates one hypothesis.

### Step 1 — Neutral site baseline

Load a site with no anti-bot: `https://example.com/`.

- **If this fails** → the browser itself is broken (engine crash, port issue,
  display/Xvfb problem). Fix the browser first. Stop diagnosing the target site.
- **If this works** → the browser engine is fine. Continue.

### Step 2 — Target site WITHOUT authentication cookies

Load the target site's public/landing page with a fresh session (no cookies
imported):

- **If the page renders content** (login form, public content, sign-up flow) →
  the browser CAN reach the site. The block is session/auth-specific.
- **If you get a redirect loop / empty page** → the site blocks the browser
  fingerprint regardless of session state. Anti-bot is filtering at the
  network/fingerprint level.

### Step 3 — Target site WITH authentication cookies

Import saved cookies into the session, then load the target URL, then snapshot
on the page.

- **If content appears and the URL matches the expected authenticated page** →
  cookies worked, anti-bot passed. Any further failure is a script/selectors
  issue. Debug the script.
- **If the page is empty but the URL changed to the expected page** → the
  browser navigated but the server served an empty DOM. This is the classic
  anti-bot fingerprint block: the server accepted the request but stripped the
  content because the browser fingerprint is flagged.
- **If you get `NS_ERROR_REDIRECT_LOOP` or similar** → the site is bouncing
  the browser between URLs. Anti-bot escalation. The entire domain is blocked.

### Step 4 — URL variation

Try different paths on the same domain:

- Homepage (`/`)
- Login page (`/login`)
- A specific profile/page (`/in/username`)
- Search results (`/search/results/people/`)

If some URLs work and others redirect-loop, the anti-bot is page-specific.
If all URLs fail, the domain is fully blocked.

## Interpreting Results

| Step 2 (no cookies) | Step 3 (with cookies) | Conclusion |
|---|---|---|
| Empty / redirect loop | Empty / redirect loop | Domain blocked at fingerprint level. Not a script bug. |
| Renders content | Empty page, URL correct | Anti-bot kills authenticated sessions. Cookies are invalid from this browser profile. |
| Renders content | Renders content | Browser works. Script/selectors are the issue. |
| Redirect loop | Redirect loop | Redirect loop escalated from page-level to domain-level. |

## Common Failure Modes

### Empty page with correct URL (the most deceptive)

The browser navigated to the right URL, the title may be set, but the AX tree
is empty and there are zero buttons/text. **This is not a script bug.** The
server served an empty response to the flagged browser fingerprint.

Do NOT spend time debugging selectors, query params, or snapshot structure when
you see this. The page literally has no DOM.

### NS_ERROR_REDIRECT_LOOP

Firefox/Camoufox error when the site bounces between URLs. Can be
page-specific (one URL loops) or domain-level (homepage also loops). Domain-level
means the anti-bot escalated — no page on the domain is reachable from this
browser profile.

### Cookies imported but session not authenticated

Cookies import via the REST API returns 200 and the cookie count is correct,
but the site serves an empty page or redirects to login. The server-side session
validation rejects the browser fingerprint. The cookies are real but unusable
from this headless profile.

## Camofox-Specific Notes

### Background process lifecycle

`npm start` in the Camofox directory launches the server. The shell wrapper
exits quickly but the actual server process (node + camoufox-bin) keeps running
in the background. A "process completed" notification for the wrapper is a false
alarm — check `ss -tlnp | grep 9377` and the log at `/tmp/camofox.log` to
verify the server is actually up.

The Camofox REST API health check is:
```
curl http://localhost:9377/
# Returns: {"ok":true,"enabled":true,"running":true,"engine":"camoufox",...}
```

### Session model

- `userId` — isolates cookies/storage between users. Different userId = different
  browser profile.
- `sessionKey` — groups tabs by conversation/task.
- Cookie import: `POST /sessions/{userId}/cookies` with `{cookies: [...]}`.
  Returns 200 + count on success, 404 if the endpoint path changed.
- Imported cookies are NOT persisted across Camofox restarts. Restarting the
  server loses all imported sessions. Re-import after every restart.

### Anti-bot behavior on LinkedIn

- Login page (`/login`) renders without cookies — browser can reach LinkedIn.
- Homepage with cookies → empty page (URL changes to `/hp` but DOM is blank).
- Profile pages and search → `NS_ERROR_REDIRECT_LOOP`.
- 24 cookies (li_at, JSESSIONID, etc.) import successfully but server-side
  session validation fails from the Camoufox fingerprint.
- The anti-bot escalated from page-level to domain-level blocking during the
  session — homepage went from accessible to redirect-loop.

## False negatives: a probe that lies to you (measured 2026-09-29)

The four-step test above assumes the **probes themselves are sound**. They are
not always. Two measured cases where a correct session was reported broken,
and each one would have sent you off to fix a system that was fine.

### `HttpOnly` cookies are invisible to JS — always

```js
document.cookie.includes('auth_token')   // false, even when fully logged in
```

`auth_token` (X) and `li_at` (LinkedIn) are `HttpOnly`. No script in the page,
including your own, can read them. **A `false` here is the expected result for a
perfectly healthy session** and says nothing about auth state.

Corollary: never use cookie visibility as evidence of login *or* of logout.
This is not a weak signal, it is a constant false negative.

### Async-rendered UI read too early

X loads its account button asynchronously. Reading `innerText` a few seconds
after navigation returns `''` — empty, not "no account". Reading the handle
after a click, or on a SPA that re-renders, gives the same false negative.

Poll for a readiness threshold (body length, presence of a known control)
rather than sleeping a fixed interval and reading once. When a probe returns
empty, the first hypothesis is **not loaded**, and not "logged out".

### A wrong selector looks exactly like a missing feature

Measured: the Messages nav control is
`[data-testid="AppTabBar_DirectMessage_Link"]`. The plausible-looking
`AppTabBar_Message` matches **zero elements**, and the page then redirects to a
passcode screen — so the conclusion drawn was "DMs are blocked on this
account". They were not; the selector was wrong.

Rule: **a selector that matches nothing is a bug in the selector, not evidence
about the site.** Before concluding a capability is unavailable, dump the real
element (`[data-testid^="..."]` enumeration) and confirm the handle exists. This
is the same discipline that applies to hashed CSS classes — the "it's not
there" conclusion is nearly always "I looked in the wrong place".

### Two different login gates produce the same symptom

X redirects to `/i/chat/pin/recovery` when Messages is opened. That looks like
a session or automation failure and is neither — it is a separate 4-digit
encryption passcode belonging to the user. No script bypasses it, and probing
harder just yields an empty composer, which then looks like a third problem.

When a site stacks auth walls, enumerate the gates explicitly and report the
specific one that is blocking. "Logged out", "session dead", and "user action
required" are three different reports.

## Verify a write with a control, never a single probe

A 200, a closed dialog, or a vanished button is consistent with success, with
failure, and with a page that never rendered. One signal is never enough.

What actually proved a real send, from two unrelated directions at once:

- a **counter the platform itself decrements** (an invitation allowance going
  3 -> 2 -> 1 -> 0 across three profiles), and
- **re-loading the target and finding the action control gone for that
  specific target** — checked *in the same batch against a profile that was
  never acted on and still had the control*.

Without that control, "the button is gone" is indistinguishable from "the page
failed to render". With it, the pair is a genuine experiment. Always keep one
known-good target in every verification batch.

Corollary for scripting: **a foreground command that hits its timeout can tear
down the very tabs holding the session you were inspecting.** If a driver
script is navigating a logged-in SPA, run it `background=True` and poll. A
290s timeout killed 12 tabs mid-inspection in one session; the session
survived in the browser profile, but the diagnostics did not.

## The quota may not be the quota you think it is

When a platform reports a limit, establish **which budget the specific action
draws from** before concluding an action is impossible.

Measured: a dialog advertised "3 personalized invitations remaining for this
month", which reads as a hard cap on connecting. It gates *personalised*
invitations only — the same dialog's "Send without a note" path bypassed it
completely and kept working, subject to a different cap.

So "you cannot do X" and "you can do X differently, with a tradeoff" are both
true, and the first is a lie by omission. Read the counter at the moment of
action, stop at zero **on that specific path** rather than assuming a global
stop, and report the two numbers separately along with the tradeoff (an
uncapped path may have a materially lower acceptance rate).

## What NOT to do

- **Don't debug selectors when the page is empty.** An empty AX tree means no
  DOM. No selector will find anything. Verify the page has content first.
- **Don't assume cookie import = authenticated session.** Cookie import is a
  browser-level state operation. The site's server-side bot detection operates
  independently and can invalidate the session.
- **Don't retry the same URL repeatedly after a redirect loop.** The site may
  rate-limit or further escalate. Try a different URL or a fresh session.
- **Don't trust "page loaded" from the browser engine.** Camoufox reports
  navigation success even when the server serves an empty body. Always snapshot
  on the page and check for actual content.

## When to stop

If all four diagnostic steps point to anti-bot (neutral site works, LinkedIn
fails with and without cookies, multiple URLs fail), the conclusion is that
**this browser fingerprint is blocked by this site**. Further script debugging
will not help. Options:

1. Manual login in a visible browser (the only verified bypass).
2. A different browser engine with a different fingerprint (may or may not work
   — anti-bot can detect multiple headless engines).
3. Accept the block and use an alternative channel.

## IP/Network-Level Blocking (Beyond Fingerprint)

Some sites block at the IP/ASN level in addition to browser fingerprint. This is
harder to diagnose because even non-browser HTTP clients get blocked.

### How to tell it's IP-level, not fingerprint-level

Run the same requests with a plain HTTP client (curl, Node fetch) using the same
cookies/user-agent the browser would send:

- **If curl with cookies also gets blocked** (empty response, 302 redirect, HTTP
  999, or connection drop) → the block is at the IP/network level, not the
  browser fingerprint.
- **If curl with cookies works but the browser fails** → the block is
  fingerprint-specific. Try a different browser engine.

### LinkedIn-specific finding (2026-09)

LinkedIn blocks Oracle Cloud IPs at the network level for most authenticated
Voyager API endpoints. Observed:

- `identity/me` endpoint: can work intermittently with valid cookies (returns
  profile data)
- `feed`, `search`, `connections`, profile view of others: 302 redirect or
  timeout from the same IP
- Public pages without cookies: HTTP 999 (bot-blocked)
- Headless Chromium (Patchright/Playwright) with injected cookies: homepage
  loads but serves 39-byte blank page

This means **no browser automation and no HTTP CLI tool will reliably work from
a flagged cloud IP**, regardless of cookies. The only paths that can work:

1. A different exit IP not flagged by LinkedIn (another VPS, residential proxy,
   Tailscale exit node from a non-cloud host).
2. Manual login in a real browser on a non-flagged machine, then export fresh
   cookies.
3. LinkedIn's official APIs (Marketing API, Sales Navigator API) — require
   developer approval, not available for personal automation.

### curl-impersonate as a fingerprint workaround (when block is fingerprint, not IP)

If the block is fingerprint-level (curl works, browser fails), `curl-impersonate`
can help by speaking exact Chrome/Firefox TLS:

```bash
# Build from source (needs cmake, g++, make, zlib, nghttp2, brotli, aws-lc, boringssl)
git clone https://github.com/yunolai/curl-impersonate
cd curl-impersonate && cmake -B build && cmake --build build

# Use the Chrome-impersonating curl
./build/curl_chrome119 -b "li_at=...; JSESSIONID=..." \
  "https://www.linkedin.com/voyager/api/identity/me"
```

**Prerequisites:** cmake, g++, make, zlib, nghttp2, brotli, aws-lc, boringssl.
On Oracle Linux ARM64: g++ and make are available via dnf; cmake may need
explicit install. No prebuilt ARM64 binary is published.

**Caveat:** curl-impersonate bypasses TLS/fingerprint detection, NOT IP-level
blocks. If the IP is flagged, curl-impersonate won't help.

## References

- `references/linkedin-camofox.md` — LinkedIn-specific findings with Camoufox.
- `references/linkedin-cli-tools.md` — LinkedIn CLI tool landscape and cookie-based auth tests.
- `references/fail-open-guards-and-multi-entrypoint.md` — guards that return
  "allowed" when their config key is missing; a sending path that bypasses the
  DB that holds the cooldown; what to assert at startup. Read before adding a
  second entry point to any send/queue/cap system.
