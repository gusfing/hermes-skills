# X cookie import failure notes — 2026-07-28

## Issue
First Netscape-to-Playwright cookie import for X failed with:
`browserContext.addCookies: cookies[9].expires: expected float, got object`

## Root cause
Session cookies were sent as `expires: null` when no expiry was present. This Camofox build rejects `null` for `expires`.

## Fix
- For session cookies without expiry, omit the `expires` key entirely.
- Only include `expires` when it is a positive Unix timestamp number/float.

## Verification
After import, created a fresh tab and navigated to `https://x.com`. Login state confirmed via snapshot refs and screenshot showing the home timeline UI.

## Tracker path
- `/opt/data/.camofox/cookies/x_account_a_tracker.json`

## Stale-tab lesson
After Camofox browser health restarts, old tab IDs may become invalid. Resolve a fresh tab before screenshot/snapshot.

## Expiry notes
- `gt` was close to current date
- `auth_token` and `ct0` had longer horizons
