# LinkedIn + Camofox — Session Findings

## Summary

Camofox (Firefox-based headless browser via `camoufox-bin`) was tested against
LinkedIn during August 2026. The browser engine works correctly (example.com
loads, LinkedIn login page renders), but LinkedIn's anti-bot blocks
authenticated sessions.

## What Works

- **Browser engine**: example.com renders with full DOM content (237 chars AX tree).
- **LinkedIn login page without cookies**: renders 17,212 chars of content,
  showing the sign-up/join flow. Browser CAN reach LinkedIn.
- **Cookie import via REST API**: `POST /sessions/{userId}/cookies` returns 200
  with `{"ok":true,"count":24}`. All 24 cookies (li_at, JSESSIONID, etc.) import
  successfully.

## What Fails

### Homepage with cookies (empty page)

- URL changes to `https://www.linkedin.com/hp` (navigation succeeds).
- AX tree is empty. Title is `(none)`. Zero buttons, zero text.
- This is the classic anti-bot fingerprint block: the server accepted the
  request but stripped the DOM content because the Camoufox/Firefox fingerprint
  is flagged.

### Profile pages and search (redirect loop)

- `https://www.linkedin.com/in/arialdo` → `NS_ERROR_REDIRECT_LOOP`
- `https://www.linkedin.com/search/results/people/` → `NS_ERROR_REDIRECT_LOOP`
- The redirect loop escalated from profile-only to domain-wide (homepage also
  started returning empty pages during the session).

## Key Insight

The 24 imported LinkedIn cookies are real and valid (`li_at` is the primary
LinkedIn auth cookie), but **LinkedIn's server-side bot detection overrides
them** when the request comes from a flagged browser fingerprint. The cookies
establish browser-level state, but the server independently validates the
fingerprint and serves an empty/blocked page.

Cookie import ≠ authenticated session. The cookies are browser state; the
server-side anti-bot is a separate layer.

## Anti-Bot Escalation Observed

During the session, LinkedIn's blocking escalated:

1. **Early**: Profile pages returned "Problem loading page" (empty DOM, title set).
2. **Later**: Homepage started returning empty DOM too (URL `/hp`, no content).
3. **Later still**: Profile pages and search triggered `NS_ERROR_REDIRECT_LOOP`.

This is domain-level blocking. No page on LinkedIn is reachable from this
Camoufox profile once escalated.

## Script-Specific Observations

All LinkedIn automation scripts (linkedin_message.js, post_linkedin.js,
linkedin_campaign.js) passed syntax checks and `--dry-run`. At runtime they
failed because the page had no DOM — not because of selector bugs. The scripts
correctly reported `not_found` for buttons that didn't exist (because the page
was empty).

## Verification Commands

```bash
# Camofox health
curl http://localhost:9377/
# {"ok":true,"enabled":true,"running":true,"engine":"camoufox","browserConnected":true,...}

# Check port
ss -tlnp | grep 9377

# Check log
tail -30 /tmp/camofox.log

# Import cookies (Node.js)
# POST /sessions/{userId}/cookies
# Body: { "cookies": [ {...}, ... ] }
# Response: { "ok": true, "userId": "...", "count": 24 }

# Create tab
# POST /tabs
# Body: { "userId": "...", "sessionKey": "...", "url": "https://..." }
# Response: { "tabId": "...", "url": "...", "title": "..." }

# Get snapshot
# GET /tabs/{tabId}/snapshot?userId={userId}
# Response: { "url": "...", "title": "...", "snapshot": "AX tree text..." }
```

## Cookies File Location

`/home/opc/.hermes/outreach/linkedin-cookies.json` — 24 LinkedIn cookies.
This file survives Camofox restarts but must be re-imported after each restart
(via `POST /sessions/{userId}/cookies`).

## When to Use This Reference

Load this when running `browser-anti-bot-diagnosis` against LinkedIn. The 4-step
test sequence from that skill applies here:

1. example.com → works (browser OK)
2. LinkedIn without cookies → login page renders (site reachable)
3. LinkedIn with cookies → empty page / redirect loop (anti-bot blocked)
4. URL variation → all LinkedIn URLs blocked

Conclusion: this Camoufox fingerprint is blocked by LinkedIn. Further script
debugging will not help.
