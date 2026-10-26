# X Composer Workarounds

## Verified behavior

- In Camofox, clicking the `Post` accessibility ref on X often stays on `/home` and does not reliably open the composer.
- JS-based composer open via `evaluate` can bring up the inline composer when ref clicks cannot.
- Media upload automation via browser refs/snapshots is unreliable on X; use manual-complete handoff when needed.

## Validated JS snippet

```js
(() => {
  const candidates = Array.from(document.querySelectorAll('[data-testid="tweetTextarea_0"], [href="/compose/post"], [data-testid="SideNav_NewTweet_Button"], a[href="/compose/post"]'));
  const el = candidates.find(e => e.offsetParent !== null || e.tagName === 'A');
  if (!el) return 'no_candidate';
  el.click();
  return 'clicked';
})()
```

## Auth-health notes

- Ignore `__cf_bm` expiry/health alerts; it is a short-lived Cloudflare tracker, not an auth signal.
- Prefer `auth_token`, `li_at`, and `li_rm` as the actual auth-cookie signals.
- This Camofox build rejects `expires: null`; omit `expires` for session cookies.

## VNC/container note

- VNC interactive login requires `x11vnc`, `novnc`, and `python3-websockify`.
- In restricted containers without package-manager/sudo/`unshare`, VNC is typically unavailable.
- Docker deployments often include VNC support out of the box.
