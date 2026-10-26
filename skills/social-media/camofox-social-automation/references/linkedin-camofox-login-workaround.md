# LinkedIn Camofox Login Workaround

## Problem
Netscape cookie import for LinkedIn often returns success but the session
still shows login page or redirects to `/uas/login`.

## Why
- LinkedIn session has server-side state beyond cookies
- `li_at` lifetime does not guarantee fresh session acceptance
- IP/fingerprint/browser profile mismatch can invalidate cookies

## Verified approach
1. Open Camofox LinkedIn login page once
2. Have user complete manual login
3. Reuse same `userId`/`sessionKey` thereafter
4. Do not rely on passive cookie import alone

## Fallback
Use Chrome CDP if Chrome has an active LinkedIn session.
