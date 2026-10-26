# Auth-only cookie tracking + storage state fallback

## What was fixed

- Previous cookie checker flagged short-lived cookies like `__cf_bm` as expiring soon, creating false urgency.
- Real auth cookie lifetimes are much longer if preserved properly.

## Auth-cookie hints by provider

**X/Twitter**
- Primary: `auth_token`
- Secondary: `ct0`, `twid`
- Lifetime: often long-dated in exports

**LinkedIn**
- Primary: `li_at`
- Secondary: `li_rm`
- Lifetime: often long-dated in exports

**Google/Gmail**
- SID/HSID/SSID/APISID/SAPISID family
- `__Secure-1PAPISID`, `__Secure-1PSID`
- `__Secure-next-auth.session-token` for ChatGPT

## Best-practice durable pipeline

1. Import cookies after each fresh export
2. Verify login state via page snapshot, not just import HTTP 200
3. Track auth cookies, not all cookies
4. If long-lived login is critical, prefer capturing full `storageState()` from an authenticated browser context over raw cookie files alone

## Files in use

- `/opt/data/scripts/camofox_cookie_check.py` — auth-only checker; reports the weakest auth cookie per account
- `/opt/data/.camofox/cookies/*_tracker.json` — per-account auth cookie expiry tracking
- `/opt/data/.camofox/storage_state/` — planned full-session export destination when endpoint is available
