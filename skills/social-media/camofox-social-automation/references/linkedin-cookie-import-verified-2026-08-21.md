# LinkedIn Camofox Login Workaround

## Problem
Netscape cookie import for LinkedIn often returns success but the session
still shows login page or redirects to `/uas/login`.

## Why
- LinkedIn session has server-side state beyond cookies
- `li_at` lifetime does not guarantee fresh session acceptance
- IP/fingerprint/browser profile mismatch can invalidate cookies

## Verified approach (2026-08-21)
In this environment (Camofox v1.13.1, full Netscape cookie set with
`li_at`, `JSESSIONID`, `li_rm`, etc.), **cookie import CAN result in a
working LinkedIn session**.

**Tested cookie set (20+ cookies):**
`li_sugr`, `bcookie`, `bscookie`, `g_state`, `_guid`, `aam_uuid`,
`li_theme`, `li_theme_set`, `dfpfpt`, `visit`, `li_rm`, `s_fid`, `mbox`,
`lang`, `liap`, `JSESSIONID`, `li_at`, `imegapola`, `timezone`, `lidc`,
`s...[truncated]