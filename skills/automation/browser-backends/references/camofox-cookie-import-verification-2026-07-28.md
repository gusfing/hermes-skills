# Camofox cookie import + multi-account verification — 2026-07-28

Observed behavior when importing Netscape cookies into Camofox via
`POST /sessions/:userId/cookies`.

## Failure signature

- Endpoint: `/sessions/:userId/cookies`
- Error: `browserContext.addCookies: cookies[N].expires: expected float, got object`
- Cause: payload contains `expires: null` or a non-numeric value.

## Workaround

Normalize `expires` before import:
- numeric timestamp → keep as number
- missing / session cookie → **omit** the field entirely
- never send `null`

## X / LinkedIn results

- `x_account_a`: import accepted with 13 cookies; homepage snapshot showed
  logged-in home timeline with profile identity and compose UI.
- `linkedin_account_a`: import accepted with 25 cookies; homepage snapshot
  showed logged-in LinkedIn with profile/admin areas visible.

## X compose automation caveats

Modern composer UIs on X/LinkedIn often break accessibility-ref automation.
Observed behavior:
- compose link may open without an editable media composer
- ref clicks can reset navigation back to home
- media upload inputs may not fire from accessibility-layer clicks

If a social site doesn't expose a stable ref-driven composer flow in Camofox,
stop and choose a safer path:
- manual post from a real browser
- platform-native API if available
- simpler text-only post before retrying media upload

## ChatGPT result

- Import accepted with 14 cookies.
- Verification snapshot still showed `Log in` / `Sign up for free`.
- Conclusion: cookies alone did not establish an active ChatGPT session in
  Camofox. Next candidates: stricter required cookies, token binding, or
  IP/browser-fingerprint validation.

## Tracked auth-cookie dates from session

X (`x_account_a`):
- `gt` → 2026-07-28 09:57 UTC
- `auth_token` → 2027-07-28 07:28 UTC
- `twid` → 2027-07-28 07:28 UTC
- `ct0` → 2027-09-01 07:28 UTC

LinkedIn (`linkedin_account_a`):
- `li_at` → 2027-07-28 07:34 UTC
- `li_rm` → 2027-07-28 07:34 UTC
- `bcookie` → 2027-07-28 07:34 UTC
