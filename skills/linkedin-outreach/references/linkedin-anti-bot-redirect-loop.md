# LinkedIn Anti-Bot: Redirect Loop vs Network Error

## Two distinct failure modes from 2026-08-21 testing

LinkedIn's anti-bot produces different symptoms depending on which endpoint is hit and how the browser fingerprint is flagged. Both are server-side blocks, not script bugs.

### Symptom A: `NS_ERROR_NET_EMPTY_RESPONSE` (feed + profile)

```
Navigating to https://www.linkedin.com/feed/
  → NS_ERROR_NET_EMPTY_RESPONSE
  Call log: navigating to "https://www.linkedin.com/feed/",
            waiting until "domcontentloaded"
```

Also seen on `/in/<profile>/` URLs. The error comes from the Firefox networking layer — LinkedIn drops the connection entirely rather than returning a page. This is the first symptom observed in this session.

### Symptom B: "The page isn't redirecting properly" (profile, 2026-08-21)

```
Navigating to https://www.linkedin.com/in/arialdo
  → Tab loads a Firefox error page:
     "The page isn't redirecting properly"
     "Camoufox can't connect to the server at www.linkedin.com"
     "The site could be temporarily unavailable or too busy."
     Button: "Try Again" [e1]
```

Snapshot returns an AX tree with just the error page — no buttons, no profile content, no LinkedIn UI. JavaScript evaluation finds no buttons on the page.

**Key difference:** Symptom A is a network-level empty response. Symptom B is a Firefox-level redirect loop detection. Both indicate LinkedIn is blocking the browser profile, but they manifest differently and require different diagnostic approaches.

## Diagnostic flow

When a LinkedIn automation script reports "can't find Connect/Message button" or "not on profile":

1. **Check the snapshot URL** — is it the expected profile URL or an error/login page?
2. **Read the AX tree** — is it a normal LinkedIn page or an error page?
3. **If redirect loop:** the profile is blocked. Clicking "Try Again" does not break the loop (LinkedIn re-blocks on retry).
4. **If NS_ERROR_NET_EMPTY_RESPONSE:** the feed is blocked. Same root cause, different manifestation.

## What does NOT break the block

| Attempt | Result |
|---|---|
| Click "Try Again" on redirect loop page | Re-blocks immediately |
| Import more/different cookies | No effect — server-side session validation fails |
| Navigate to homepage first, then profile | Homepage loads (or redirects to hp), profile still blocked |
| Different sessionKey / userId | Same behavior |
| Wait and retry | Same block |

## Cookie import behavior

REST API accepts cookies and returns `{"ok":true,"count":N}` but the browser context does not become authenticated. LinkedIn's server-side session check validates beyond cookie values — browser fingerprint, IP, and behavioral signals all factor in. The `li_at` token alone is insufficient.

This was verified with 24 cookies (including `li_at`, `JSESSIONID`, `PLAY_SESSION`, `AMCV`) imported via `POST /sessions/linkedin_main/cookies`.

## When to declare "LinkedIn blocked" in a session

Declare it when:
- Profile URL snapshot shows redirect loop error page, OR
- Feed URL returns NS_ERROR_NET_EMPTY_RESPONSE, AND
- Cookie import was attempted and accepted but session is not authenticated

Do NOT retry the same approach more than once — the block is deterministic for the browser profile.
