# X composer automation in Camofox

## Verified success pattern

Opening the X composer by accessibility ref click is brittle in Camofox.
Repeated clicks of `Post`, `/compose/post`, and inline composer refs
often landed on home instead of keeping the compose modal open.

Working opener uses `evaluate`:

```js
(() => {
  const candidates = Array.from(document.querySelectorAll(
    '[data-testid="tweetTextarea_0"], [href="/compose/post"], [data-testid="SideNav_NewTweet_Button"], a[href="/compose/post"]'
  ));
  const el = candidates.find(e => e.offsetParent !== null || e.tagName === 'A');
  if (!el) return 'no_candidate';
  el.click();
  return 'clicked';
})()
```

Expected result:
- URL becomes `https://x.com/compose/post`
- Snapshot shows `dialog` with `textbox "Post text"`
- Toolbar includes `button "Add photos or video"` and `button "Choose File"`

## Media upload blocker

Even when the composer opens, media attach often does not complete:
- ref click on `Add photos or video` can reset navigation to home
- hidden file input exists, but direct JS upload is blocked by browser security
- this is a known fragility, not a Hermes tool bug

Stop condition:
- do not retry more than once after the page unexpectedly navigates home
- report the exact snapshot state and pause media posting

## Recommended fallback order

1. Text-only post if acceptable
2. Manual submit inside Camofox with pre-opened composer
3. Platform-native API media upload if available
4. Later: interactive login via VNC or external storage-state export

## What was confirmed

- text typing works into the X compose textbox
- cookie-backed login is valid for X account `Kunal Sharma @Kunalsharmadec6`
- cookie-backed login is valid for LinkedIn account `Kunal Sharma`
- auth-cookie expiry is ~1 year for the real login tokens
- Camofox does not expose `/sessions/:userId/storage_state` in this build
- VNC plugin source exists, but interactive VNC is unavailable in this container
