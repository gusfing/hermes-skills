# Playwright cookie-backed X posting workaround

## When to use

Use this when:
- Camofox shows a logged-in X UI
- but `/tabs/{tabId}/type` into `[data-testid="tweetTextarea_0"]` leaves the Post button disabled
- or overlay/mask intercepts pointer events for the composer

## Why it works

Camofox type + snapshots still left X’s React store empty.
Playwright’s real keyboard/input pipeline does reach the composer reliably
when the session has valid `auth_token` and `ct0` cookies.

## Steps

1. Collect minimal cookies from export:
   `auth_token`, `ct0`, plus domain/path `/.x.com` or `x.com`
2. Launch Playwright Chromium
3. `context.addCookies(cookies)`
4. `page.goto('https://x.com/compose/post', { waitUntil: 'domcontentloaded' })`
5. Wait 3-5s
6. `await page.focus('[data-testid="tweetTextarea_0"]')`
7. `await page.keyboard.type('hello world', { delay: 40 })`
8. Wait 1.5s
9. `await page.keyboard.press('Control+Enter')`
10. Wait 5s
11. Verify:
    - `page.url()` changed from `/compose/post`
    - or success toast says post sent
    - or screenshot shows confirmation

## Known failure mode

If playwright click on textbox times out because of a mask/overlay from `#layers`:
- do not keep clicking
- use `page.focus(...)` instead of click
- press Escape before typing to dismiss overlays
- take screenshot before submit

## Repo scripts

- `scripts/post_x_cookies.js` — cookie import + compose + submit + screenshot
- `scripts/post_x_final.js` — focused single-shot attempt