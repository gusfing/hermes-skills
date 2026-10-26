---
name: x-automation
description: |
  Automation for X/Twitter posting, media uploads, and engagement workflows.
  Covers cookie-backed browser posting, React composer quirks,
  and direct API patterns. Use this skill when the user asks to:
  post to X/Twitter, upload media to a tweet, automate X engagement,
  or diagnose X composer/submit failures.
version: 1.0.0
tags: [x, twitter, social-media, automation, playwright, posting]
---

# X Automation

Use this skill when the user asks to:
- post to X/Twitter from automation
- attach media/images to tweets
- build reusable X posting workflows
- diagnose why X submit/React composer doesn’t fire

## Backend selection

```
Playwright + exported cookies → X web API → Camofox/manual handoff
```

### Primary: Playwright + cookies
- Most reliable for React contenteditable composer
- Works without logging in if `auth_token` + `ct0` are imported as cookies
- Reuses lightweight Chromium from `playwright install`

### Secondary: X web API (from within browser context)
- Use when button-layer submit routes fail but same-page GraphQL calls may work
- Call from `page.evaluate()` to reuse the authenticated browser session
- Captured live headers from `page.on('request')` give valid `authorization` and `x-csrf-token`

### Fallback: Camofox/manual
- Camofox keyboard input often doesn’t sync with X’s React state
- Use only if Playwright session is unavailable

## Cookie requirements

Minimum auth cookies to import:
```js
{ name: 'auth_token', value: '<value>', domain: '.x.com', path: '/' }
{ name: 'ct0', value: '<value>', domain: '.x.com', path: '/' }
{ name: 'twid', value: 'u%3D<userId>', domain: '.x.com', path: '/' }
```

Optional but helpful:
- `lang`, `dnt`, `personalization_id`
- Ignore `__cf_bm` and `guest_id_*` for auth validation

## Verified post flow

```js
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    executablePath: '/opt/data/.playwright/chromium-1234/chrome-linux64/chrome',
    args: ['--no-sandbox','--disable-gpu']
  });
  const context = await browser.newContext();
  await context.addCookies([...COOKIES]);
  const page = await context.newPage();

  await page.goto('https://x.com/compose/post', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  await page.focus('[data-testid="tweetTextarea_0"]');
  await page.keyboard.type(TEXT, { delay: 40 });
  await page.waitForTimeout(1500);

  await page.evaluate(() => {
    const btn = document.querySelector('[data-testid="tweetButton"]')
            || document.querySelector('[data-testid="tweetButtonInline"]');
    if (btn) btn.click();
  });

  await page.waitForTimeout(5000);
  console.log('final_url=' + page.url());

  await page.screenshot({ path: 'x-post-result.png' });
  await browser.close();
})();
```

## Verification — poll the feed, never trust the toast

Do NOT treat "clicked Post, no error returned" as success. On a measured
2026-09-29 run the new post was **absent at a 6s check and present at 39s** —
X renders the new timeline item asynchronously. A single early check produces a
false negative that then gets reported as a failed post.

```js
async function confirmPost(page, handle, firstLine) {
  for (let i = 0; i < 3; i++) {
    await page.goto(`https://x.com/${handle}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(9000);
    const body = await page.evaluate(() => document.body.innerText || '');
    if (body.includes(firstLine)) return true;   // measured presence, not inference
  }
  return false;  // report as "dispatched, unconfirmed" — never as posted
}
```

Poll, don't sleep-and-check-once. And if it is not confirmed, say
`dispatched only` rather than rounding up.

## Posting to a Community (measured DOM path)

Community posting works and does **not** need the API. Measured 2026-09-29 on a
logged-in desktop session. The traps are the reason this looks broken when it
is not:

| Thing | Reality |
|---|---|
| Audience control | `button[aria-label="Choose audience"]` — **has no `data-testid` at all** |
| Label after selection | `aria` flips to `Change audience`, `innerText` is the community name |
| Community rows | `role="menuitem"` — **not** `menuitemradio`, not `option` |
| Row container | nested in `[data-testid="cellInnerDiv"]` — a virtualized grid, so rows not yet scrolled into view do not exist in the DOM |
| Row click | needs `force: true` — a `[data-testid="mask"]` overlay intercepts pointer events and the click otherwise times out after 30s |

```js
await page.click('button[aria-label="Choose audience"]');
await page.waitForTimeout(3500);
const row = await page.locator('[role="menuitem"]', { hasText: 'SaaS & AI' }).first();
await row.click({ force: true });          // mask intercepts without force
await page.waitFor_timeout(3000);
// assert before typing: the audience is now set
const aud = await page.locator('button[aria-label="Change audience"]').innerText();
```

There is **no composer inside a community page** (`/i/communities/<id>` has
zero `[contenteditable]`). You post from `/home` and set the community as the
audience. The left tab rail listing your communities is a *feed filter*, not an
audience selector — clicking it does not attach the post to that community.

Always assert the audience label before typing the body. Confirm with the poll
above, and note that a community post may not appear in the community's own
Latest feed if that feed fails to hydrate — the profile feed is the reliable
witness.

Session detail and the measured community list: `references/community-posting.md`

## Media upload — measured path (2026-10-01, logged-in desktop session)

There is **no file dialog to click**. The media button opens a menu whose only
real entry is "Upload photo", and behind that sits a hidden
`input[type=file]`. That input is the element the menu feeds, so set it
directly rather than hunting the menu:

```python
def attach_image(pg, path):
    btn = pg.query_selector('[data-testid="mediaButton"]') \
       or pg.query_selector('button[aria-label="Add photo or video"]')
    if btn:
        btn.click(force=True); pg.wait_for_timeout(2500)
        up = pg.query_selector('text=/^Upload (photo|video)$/i')   # menu entry
        if up:
            up.click(force=True); pg.wait_for_timeout(2000)
    fi = pg.wait_for_selector('input[type="file"]', timeout=15000)
    fi.set_input_files(path)
    pg.wait_for_timeout(4500)
    crop = pg.query_selector('button[data-testid="cropConfirm"]')  # crop dialog
    if crop:
        crop.click(force=True); pg.wait_for_timeout(2500)
    # PROOF of attachment — never assume setInputFiles worked
    return pg.evaluate("""()=>document.querySelectorAll(
        'img[src^="blob:"], img[src*="pbs.twimg.com/media"]').length""") > 0
```

Verified live: `blobImgs: 1`. Notes that cost time:

- The `blob:` preview node is the only reliable "did it attach" signal. The
  file input reports `files: []` after upload — that is normal, not a failure.
- `data-testid="mediaButton"` **disappears** once media is attached, so probe
  for preview nodes, not for the button.
- Attach **after** typing the body, before clicking Post.
- Test the attach path **without posting**: open the composer, attach, then
  Escape + click Discard. Verify the composer is empty afterwards — a
  `text=/Discard/` click can leave the draft in place, and a stray test draft
  is a real post.

## Getting the permalink of a post you just made

**Never scrape `innerText` for `/handle/status/<id>` — it is not there.** X
renders the status id only in the `href` attribute. An `innerText` regex
returns `None` silently, every time, and you store linkless posts that look
fine for weeks.

```js
// Playwright evaluate takes exactly one argument.
const sid = pg.evaluate("""(h => {
  for (const a of document.querySelectorAll('article')) {
    for (const l of a.querySelectorAll('a[href*="/status/"]')) {
      const href = l.getAttribute('href') || '';
      if (href.indexOf('/' + h + '/status/') === 0) {      // OUR handle only
        const m = href.match(/\\/status\\/(\\d{15,25})/);
        if (m) return m[1];
      }
    }
  }
  return null;
})()""", HANDLE);
```

- Scope to your own handle, or a pinned/quoted post supplies the wrong id.
- Take the anchor that contains `<time>`. **Not** the first `/status/` link in
  the article — measured 2026-10-07, that was an inline link in the tweet body
  and returned the *quoted* author's status for someone else's post. The
  `/analytics` link also carries `/status/`, so it is two ways to get a wrong
  id from one selector.
- Verify before citing: open the URL, confirm handle + a text slice. See
  `browser-action-verification` → `references/reading-conversations-on-x.md`.
- Match the post to its pool file on a **long text slice** (~70 chars), not a
  30-char prefix. A prefix match attached the wrong permalink to both posts in
  one run — and only an explicit verify pass caught it.
- `https://x.com/i/status/<id>` 307-redirects to the canonical
  `/<handle>/status/<id>`. That 307 is normal, not a failure.

## Generating post images — check for hallucinated text

When the user asks for images on posts, `image_generate` beats scraping
Google/Unsplash in-browser: scraping is bot-blocked, stock images carry
attribution and usage rights, and generated art is free and consistent.

**But these models invent text even when told not to.** Measured: an image
prompted `no text, no words, no letters` came back reading
"CONNECHIOS / CONNECTION REQUESTS". Attaching that to a public post ships a
fabricated brand name.

So, before any generated image goes near a public post:

1. Ask for it with negative wording ("absolutely no text or typography").
2. **Look at it** (`vision_analyze`) — ask "does this contain any readable
   words, letters, or numbers? yes/no first".
3. Regenerate anything that fails. Spot-check a sample, not just the first.

Naming: keep art beside the content as a sibling (`x_media/<pool-name>.png`)
and resolve by stem at post time, so adding art to a post is dropping in one
file with no code change. Resolve the mapping for **every** content item before
claiming coverage — a partial set silently posts text-only.

**Never force a post to prove a feature worked.** If the min-gap floor is not
met, say so and let the scheduler do it. Overriding your own pacing rule to
demonstrate a capability reintroduces exactly the bot-like burst behaviour the
floor exists to prevent.

## Debugging path

1. If URL lands on login/onboarding mode: re-export cookies, refresh `auth_token` expiry
2. If composer textbox click times out: try `page.focus()` + keyboard type first
3. If overlay intercepts clicks: use JS click via `page.evaluate()`
4. If Ctrl+Enter doesn’t submit: JS click is more reliable
5. If API call returns 403/301: route through `https://x.com` + full GraphQL path in browser context

## Response style

User preference is direct and concise:
- lead with blocker/fix, not diagnostic narration
- if blocked by auth, say `auth-required` and pivot once
- do not repeat paths that were already rejected
- capture failure state in one screenshot, then stop

## Reusable scripts

- `scripts/post_x_text.js` — single text tweet
- `scripts/post_x_image.js` — tweet with media attachment
- `scripts/test_x_post.js` — uniqueness-stamped test post

## Safety

- respect X rate limits and automation policies
- add delays between sends
- use unique test text when verifying pipelines to avoid duplicate blocks