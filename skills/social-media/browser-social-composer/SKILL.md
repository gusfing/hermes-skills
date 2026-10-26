---
name: browser-social-composer
description: |
  Verified fallbacks for social-platform posting when browser-automation
  click/type actions don’t reach the frontend composer (React overlays,
  masking layers, synthetic-event rejection). Encodes the working
  Playwright + exported-cookie methods for X/Twitter and the diagnostic
  checks to tell when automation succeeded versus when to stop and verify.
version: 1.1.0
tags: [browser, playwright, camofox, x, twitter, composer, posting, fallback, verification]
---

# Browser Social Composer Fallbacks

Use when:
- A logged-in social account is reachable in a browser, but native click/type still doesn't submit a post.
- An overlay intercepts pointer events on the post button.
- React-style contenteditable composer ignores synthetic keyboard/input events.
- You need to verify a post success without narration.

## Decision shortcut

| Symptom | Best tool |
|---|---|
| Post button click blocked by overlay | Playwright `page.evaluate(() => btn.click())` |
| React textbox ignores type events | Native `page.keyboard.type()` with real focus |
| No login cookies in browser context | Playwright `context.addCookies()` from exported Netscape |
| No X session anywhere | Ask user for exported cookies + handle |
| Direct API blocked by policy/headers | Do not retry; use browser path or X API token from user |
| **LinkedIn: `input[type=file]` returns 0 after the Photo click** | Click **`Upload from computer`** first — the input mounts ~3s later |
| **LinkedIn: no "Start a post" button found** | It is a DIV with an **empty `aria-label`**. Use `button,[role=button]` + text match |
| **LinkedIn: `[global-nav]` reports logged out** | That selector does not exist. Use title + `!pathname.startsWith('/login')` + `main` |
| **LinkedIn: dropdown opens but holds no items** | Synthetic `.click()` mounts an empty shell (`innerText.length == 0`). Playwright real click, then **poll up to 8s and allow a second attempt** |
| **LinkedIn: `get_by_role()` returns 0 on an element that is definitely there** | A leftover modal set the page `aria-hidden`. Clear modals (Escape, then Cancel) *before* measuring anything |
| **LinkedIn: delete a post** | dry run first; trigger → `.feed-shared-control-menu__dropdown-item` (text `Delete post`) → `.artdeco-modal` holding both `Delete` and `Cancel` |

## X verified workflow

1. Load exported `.x.com` and `x.com` cookies into a Playwright Chromium context.
2. `page.goto('https://x.com/compose/post')`.
3. `await page.focus('[data-testid="tweetTextarea_0"]')`.
4. `await page.keyboard.type(text, { delay: 40 })`.
5. Submit via JS click inside the page context:

   ```
   await page.evaluate(() => {
     const btn = document.querySelector('[data-testid="tweetButton"]')
             || document.querySelector('[data-testid="tweetButtonInline"]');
     if (btn) btn.click();
   });
   ```

6. Wait 5s; redirect to `/home` means post succeeded.

## Image media

- Find `input[type="file"]` and call `setInputFiles(absolutePath)` before submit.
- Supported formats: PNG/JPG. Large files may fail upload silently; retry unchanged only once.

## WhatsApp CDP timeout fallback

If Chrome CDP shows a WhatsApp `web.whatsapp.com` target, but `browser_snapshot`, `browser_vision`, or click/type repeatedly time out, do not keep retrying CDP. Fall back once to Playwright against the existing Chrome WhatsApp profile directory with `launchPersistentContext({headless: true, userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'})`. Reusing the profile preserves any existing login state and avoids fresh QR scans.

## WhatsApp persistent-context caveats

- WhatsApp Web rejects default Playwright/HeadlessChrome user agents; set a real Chrome UA string.
- In containers without `$DISPLAY`, use `headless: true` or wrap with `xvfb-run`.
- The page may sit on the initial WhatsApp loading screen for an extended time even with a valid profile; use `waitUntil: 'networkidle'` or wait 15–25s before declaring stuck.
- Loading screen ≠ QR code ≠ logged-in state; treat them as three distinct page states and verify before acting.

## Verify, don’t narrate

- Repost/quote buttons usually mean the composer state is still active. That is not a success.
- Search for the exact post text with `document.querySelectorAll('[data-testid="tweetText"]')` on the user’s profile timeline.
- Only declare success after matching text is confirmed live.
- Success signals: `/home` redirect, success toast, or post text visible on profile.
- Failure signals: still on `/compose/post`, composer still open, no toast.

## X profile verification by scan

- Helper: fetch profile tweets and match exact expected text.
- If nothing matches, assume failure; do not infer success from URL changes alone.
- Re-run the post attempt only when a changed condition exists: unique text, alternate submit method, or freshly restored cookies.

## Hard stops / when not to retry

- Approval-policy or timeout blocks direct HTTPS requests from terminal code.
- Canvas/screenshot vision cannot confirm posted text that is not present.
- If the overlay/mask blocks all click variants, stop asking for more permission and switch tools/backends once.
- Do not loop the same submit action without a changed condition.

## WhatsApp browser UA requirement

- WhatsApp Web rejects default Playwright/HeadlessChrome UA and browser-edge UA strings.
- Set UA to a normal Chrome UA before navigation, e.g. `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36`.
- Treat loading screen, QR login page, and logged-in chat list as three distinct states; do not treat loading screen as blocked state.
- If CDP shows a WhatsApp target but page snapshots/vision/click time out, use Playwright persistent context instead of retrying CDP.

## X image posts

- After navigate to `/compose/post` and typing text, locate `input[type="file"]` and call `await input.setInputFiles(absolutePath)` before submit.
- Supported: PNG/JPG. If upload silently fails, retry once with same file path; do not retry with different content.
- After JS click submit, wait 5–6s; success = redirect to `/home` or success toast.

## X verified workflow

1. Load exported `.x.com` and `x.com` cookies into a Playwright Chromium context with `context.addCookies(cookies)`.
2. `page.goto('https://x.com/compose/post', { waitUntil: 'domcontentloaded', timeout: 60000 })`.
3. `await page.focus('[data-testid="tweetTextarea_0"]')`.
4. `await page.keyboard.type(text, { delay: 40 })`.
5. Submit via JS click inside the page context:

   ```
   await page.evaluate(() => {
     const btn = document.querySelector('[data-testid="tweetButton"]')
             || document.querySelector('[data-testid="tweetButtonInline"]');
     if (btn) btn.click();
   });
   ```

6. Wait 5s; redirect to `/home`, success toast, or exact post text visible on profile = confirmed post.
7. If duplicate text error appears, that also confirms an earlier identical post was accepted; use unique text to disambiguate.

## X cookie requirements

- Minimum working cookie set for auto-login: `auth_token`, `ct0`, plus domain-matched entries for `.x.com` and `x.com`.
- Cookie import alone is insufficient if Playwright is launched with a headless/WebDriver UA that X treats as untrusted; use a real Chrome UA string.
- The `auth_token` value alone does not guarantee session; verify by reaching `/compose/post` without a login redirect.

## WhatsApp persistent-context and UA override

- Launch with `chromium.launchPersistentContext(profileDir, { executablePath, args: ['--no-sandbox','--disable-gpu'], headless: true, userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36' })`.
- In containers without `$DISPLAY`, use `headless: true` or wrap with `xvfb-run`.
- The page may sit on the initial WhatsApp loading screen for an extended time even with a valid profile; use `waitUntil: 'networkidle'` or wait 15–25s before declaring stuck.
- Loading screen ≠ QR code ≠ logged-in state; treat them as three distinct page states and verify before acting.
- If `web.whatsapp.com` reachability is uncertain or CDP page commands time out, use Playwright against the existing Chrome WhatsApp profile instead of looping on CDP.

## WhatsApp QR dashboard

- Create a small isolated Node server on an unused port, e.g. `3001`, separate from existing apps.
- Serve: dashboard HTML, QR screenshot PNG, JSON APIs for status, contacts, and WhatsApp start.
- **Critical:** the `/api/wa/start` handler must return immediately; launch and QR capture must happen in a detached child process to avoid blocking the route.
- Capture QR by locating `canvas` on `https://web.whatsapp.com` and screenshotting only the canvas element to `public/qr.png`.
- Reuse the local Chrome WhatsApp profile directory to preserve login state across runs.
- For tunnels, prefer order in this container: localtunnel → Serveo → direct IP exposure only. Read the remote URL from tool output; do not assume it equals localhost.

## X DM passcode gate — empty inbox is not an empty account

`x.com/messages` and `x.com/i/chat` can redirect to
`x.com/i/chat/pin/recovery`, which demands the account's 4-digit DM passcode
to decrypt message history. Observed state while gated:

- inbox renders **empty**, no error
- `x.com/i/messages/compose` returns **404**
- no `[data-testid="DmComposerInput"]` anywhere
- `document.body.innerText` still shows the logged-in chrome (nav tabs, feed)

This is the **gate**, not the account. Never report "new account", "no
conversations", or "logged out" from this state — the underlying inbox can
be full of history. Clear the gate first, then re-probe.

The passcode belongs to the user; ask for it rather than guessing. To enter:
focus the field, `keyboard.type(passcode, { delay: 120 })`, then `Enter`.
Success = drop to `/i/chat` with the passcode text gone.

Once cleared, the new-message composer opens from
`[data-testid="dm-new-chat-button"]`, and its recipient field is
`input[data-testid="new-dm-search-input"]`. Reach the Messages tab via
`[data-testid="AppTabBar_DirectMessage_Link"]` — the testid is
`AppTabBar_DirectMessage_Link`, not `Message`.

`auth_token` reading `false` from JS is **expected** — it is `HttpOnly`, so
no script can see it. That is not a logout signal, and treating it as one is
a false conclusion the check is designed to invite.

## Poll for the new post — the render gap is real and it is not a failure

Measured 2026-09-29: a post dispatched to a community, then checked at **6s**
and reported "not confirmed"; re-checked at **39s** it was live on the profile
with a permalink. X renders the new timeline item asynchronously, and a
single sleep-then-check is guaranteed to produce a false negative on a fast
dispatch.

```js
async function confirmPost(page, handle, firstLine, tries = 3, wait = 9000) {
  for (let i = 0; i < tries; i++) {
    await page.goto(`https://x.com/${handle}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(wait);
    const body = await page.evaluate(() => document.body.innerText || '');
    if (body.includes(firstLine)) return true;
  }
  return false;
}
```

A miss after all attempts means "dispatched, unconfirmed" — say that. Never
round it up to "failed" and never to "posted".

## Replies: diagnosed and fixed — the dialog collides with the feed composer

A reply flow that clicked `[data-testid="reply"]`, typed into
`[data-testid="tweetTextarea_0"]`, and clicked `[data-testid="tweetButton"]`
ran **without a single error** and the reply was **not on the profile**.

**Root cause (measured, not guessed):** the home-page composer is *also*
`[data-testid="tweetTextarea_0"]`. A global query types into the feed
**behind** the reply modal, so the dialog's Reply button stays `disabled`
forever. The click returns cleanly and nothing is sent — no error is the
expected result of a lost reply.

The fix, all three parts required:

```python
dlg = pg.query_selector('[role="dialog"]')            # 1. scope
box = dlg.query_selector('[data-testid="tweetTextarea_0"]')
btn = dlg.query_selector('[data-testid="tweetButton"]')  # 2. tweetButton, not Inline
...
if btn.is_disabled():                                   # 3. check before clicking
    pg.keyboard.press("Escape"); continue
btn.click()
pg.wait_for_timeout(3000)
if pg.query_selector('[role="dialog"]'):                # a real dispatch CLOSES it
    pg.keyboard.press("Escape"); continue              # still open = not sent
```

The dialog-closing check is the cheapest confirmation available and needs no
extra navigation. Re-verified live afterwards: both replies then appeared on
`/HANDLE/with_replies` at 1–3 minutes old.

Reply bodies pulled from a fixed list of 8 substance points produced two
replies in one run sharing a clause — visibly the same person twice. Track
what was used in the current session, or widen the pool.

## Long CDP/Puppeteer operations: always background them

A foreground browser script that hangs is killed at the tool timeout, and on
a shared CDP connection the kill can take **every page in the context** with
it. One 290s foreground timeout collapsed a 12-tab X session to a single
LinkedIn tab; the session itself survived in the profile, but the tabs were
gone and had to be reopened.

Run any CDP/Playwright step that touches navigation, waits, or retries with
`background=true, notify=true` and poll it, so a timeout stops the wait and
not the browser. Verify the tab count before and after any long run.

## X communities posting — the audience picker (verified)

**Superseded:** an earlier revision of this skill said the audience control
"was not located" and that community posting was unavailable. That was wrong.
It was caused by probing `[data-testid$="addAudience"]`, which returns 0 because
**the control has no `data-testid` at all**. The verified path:

1. On `/home`, wait for `[data-testid^="tweetTextarea"]` with
   `page.wait_for_selector` (a bare `query_selector` at 7s often returns `None`
   and throws on `.click()`).
2. Click the composer to focus it.
3. The audience button is **`button[aria-label="Choose audience"]`** — a
   button whose visible text is `Everyone`. It has no `data-testid`; the
   `aria-label` is the only handle. After selecting, the same button reads
   `Build in Public` and its aria-label becomes `Change audience`.
4. The picker lists `My Communities` with member counts.
5. Community rows are **`[role="menuitem"]`** — not `menuitemradio`, not
   `option`, not `radio`. They live inside a virtualized `cellInnerDiv`, so a
   scan that skips `menuitem` finds nothing and looks like an empty picker.
6. **The row click needs `force=True`.** A modal `[data-testid="mask"]`
   intercepts pointer events and a normal click times out after 30s
   (`subtree intercepts pointer events`). Same failure shape as a sticky
   header dropdown over a button.
7. **The picker mounts only a SLICE of your communities.** Verified visible on
   first open: Build in Public, Indie Hackers, SaaS & AI, Indiemakers, Branding.
   `Bootstrapped Startup Founders` was **not** mounted, and a single scan
   returned `community row not found` — indistinguishable from "you are not a
   member of that community". Escalate: (a) type into the picker's own search
   input and re-scan, (b) `mouse.wheel(0, 420)` to scroll the virtualized grid
   and re-scan each time. All three paths verified working.
8. **Read the audience button back before typing and again before submitting.**
   It must print the community name, not `Everyone`.

Verified output: `menuitem found: True Build in Public | 267.9K Members` →
`AUDIENCE NOW: Build in Public`.

Two guards on the submit button that caused real confusion:

- `tweetButtonInline` is the live Post button. If it reports
  `disabled: True` while text is staged, **a submit is already in flight** —
  do not report `NO POST BUTTON` and do not re-click in a loop. Poll the
  composer char count and the button's disabled state instead.
- A community post carries an `a[href*="/i/communities/"]` link inside its
  `<article>`. No such link = personal timeline, regardless of what the
  audience button said.

Other measured facts:

- A community page (`x.com/i/communities/<id>`) has **zero**
  `[contenteditable]` elements. `hasComposer: false` there is normal — there is
  no composer to find, and hunting for one is wasted effort.
- Selecting a community tab in the home rail (`[role="tab"]`) **only filters
  the feed**. It does not attach the community as audience. This is what made
  the first post land on the personal timeline.

Enumerate joined communities from `https://x.com/<handle>/communities` via
`a[href^="/i/communities/"]` matched with
`^\\/i\\/communities\\/(\\d+)$`, taking `innerText` for the name;
`/i/communities/suggested` is not a joined community. Membership shows as the
literal word `Joined` near the member count.

## When the user says the thing was never broken

They are usually right, and the response is to go enumerate the DOM — not to
defend the probe or restate the failed check. Three times in one session this
was the correct call, and twice the user's correction arrived while I was still
mid-diagnosis.

The fast repair, in order:

1. Go straight to the primary record (profile, Sent folder, DB row), not the
   place you originally looked.
2. Dump **every** attribute you can see on the expected element, including
   `aria-label` and the ancestor chain, and paste the output.
3. State plainly that the earlier conclusion was wrong, name the bad probe, and
   move on. Do not re-argue it, do not soften it into "I may have been
   premature."

Do not treat a user correction as a negotiation. Re-run the check the right
way and report what it actually says.

## Media cross-posting: split what is solvable from what is walled

"Post my video to X and LinkedIn daily" looks like one request and is two very
different problems. Establish which half is blocked **before** quoting effort,
and say which is which.

- **Getting the media off a source platform** is usually solved — `yt-dlp`
  handles Instagram reels and posts. The failure is almost never the download.
- **X** accepts uploads from a logged-in browser session. Fine.
- **LinkedIn has no API that permits automated video posting.** The official API
  is limited to approved Community Management partners, or a personal account
  driven manually in a browser session. So the LinkedIn half is *only ever* a
  browser automation, running daily, indefinitely.

That last one is the honest answer, and it should be raised before writing code
rather than after. A daily automated video post to a profile that is also
running connection-request automation concentrates automated-looking behaviour
on one account, and that is how a profile gets restricted. Recommend shipping
one channel, letting it run a week, then deciding on the second with data.

Also confirm the *account*: if a brand account exists next to the personal one,
video is brand content and the login used decides who posts it.

## A selector that matches nothing is evidence about the selector

Three false negatives in one session, all the same shape — I picked a
selector, got zero, and reported a fact about the product:

| Probe | False conclusion | Reality |
|---|---|---|
| `[data-testid$="addAudience"]` → 0 | community posting broken | control has no testid; use `aria-label` |
| DM inbox rendered empty | account is new | passcode-recovery page rendering |
| post text absent from community feed | post failed | live on profile with a permalink |

Before reporting any capability absent, **enumerate** roles, `aria-label`s,
`data-testid`s, leaf text, and the ancestor chain of the element you expected,
and show that output. A missing `data-testid` says nothing about whether an
element exists — several X controls are `aria-label`-only.

Absence-of-evidence needs positive evidence of absence: an error, a paywall
message, a 4xx body. A query that matched nothing is never that.

Corollary: a page rendering **zero** items where it rendered 3 a minute ago is
a render failure, not an empty dataset. Re-navigate and say so.

When the user says "it was never broken," they are almost always right — go
enumerate the DOM rather than defending the probe.

## Posting volume specs: build it, then push back with numbers

Users hand over growth "operating systems" with fixed cadence — 8 posts/day,
2 community posts, engagement every 30 min, plus DMs. **Build the whole thing
mechanically, then name the two or three numbers that cannot hold, and offer a
ramp.** Do not silently comply, and do not refuse to build it.

Measured 2026-09-29 on a real account, what actually happened:

| Spec item | Reality on a young/dormant profile |
|---|---|
| 8 feed posts + 2 community per day | Fine mechanically; the pattern itself is the risk. From an account with 3 DM conversations in 6 weeks, 10 automated posts/day is the profile that gets limited. Recommend **4 + 2 first**, scale only after real impressions land. |
| "2-3 DMs every 30 min" (~40-50/day) | Hard cap is **~20/day**. The spec cannot be met. Leave the DM leg **off by default** in code and say why — silently honoring it burns the account. |
| "research what is performing on X first" | Doable read-only: search queries with `lang:en` and `min_faves`, harvested into a pool file. Keep the harvest **separate from the sender** so research never becomes a write path. |

Make the style rules **executable**, not aspirational. A `validate()` gate plus
a pool checker that fails non-zero (no hashtags, char cap, banned corporate
tells like *leverage*/*seamless*/*game-changer*, hook marker in the first line,
all hook styles represented) turns a prompt into something a cron run cannot
ship past. Rotating from a pool of files with a used-set is what keeps 10 posts
from reading as 10 copies.

One thing to surface proactively: if a **brand account** exists alongside the
personal one, posting automation from the personal login may be the wrong
account entirely. Ask before a multi-week cadence locks in.

## Verify, don't narrate — and check every surface before declaring failure

- Repost/quote buttons usually mean the composer state is still active. That is not a success.
- Search for the exact post text with `document.querySelectorAll('[data-testid="tweetText"]')` on the user’s profile timeline.
- Only declare success after matching text is confirmed live.
- Success signals: `/home` redirect, success toast, or post text visible on profile.
- Failure signals: still on `/compose/post`, composer still open, no toast.

**A cleared composer is unverified, not failed.** A JS submit click that
returns cleanly and empties the textarea has cleared the weak bar, nothing
more. Before telling the user a post did not publish, check the surfaces in
this order, because any single one can be empty for a post that worked:

1. the **author's own profile** timeline — where a community-less post lands
2. the canonical permalink, pulled from the DOM as `/<handle>/status/<id>`
3. the target community's Latest feed — the *only* one of the three that can
   look empty for a successful post

Check at least the first two before reporting a negative. Reporting "it
failed" off one empty surface is a false negative, and it is as wrong as
inventing a success — the user is looking at the thing you are describing.
When your result contradicts the user, re-check the other surface before
defending the first one.

Confirm also *which account* posted: the browser profile and the personal
handle are not necessarily the brand account the user had in mind.

## LinkedIn via raw CDP — the composer is not the X composer

LinkedIn was added 2026-10-06 and none of the X selectors carry over. The
short version, all measured on a live account:

- **Login probe:** `[global-nav]` does not exist, so that check reports a
  healthy session as logged out and the run aborts before starting. On `/feed/`
  `article`, `[role=main]`, `[role=feed]`, `.tiptap`,
  `.feed-shared-update-v2` are all `false`; only `<main>` is true.
- **"Start a post"** is a **DIV** with `role=button` and an **empty
  `aria-label`** — `querySelectorAll('button')` never returns it.
- The editor is **`.tiptap.ProseMirror[role=textbox]`**, contenteditable. There
  is no `<textarea>` to type into, and the Post button is `disabled` until the
  body has content.
- **The file input mounts only after clicking `Upload from computer`.** Probing
  for it right after the Photo click returns 0 and reads like "no upload here"
  when it is simply not there *yet*.
- **Verify the attach with `input.files.length`, not an `img` count.** A check
  scoped to `[role=dialog] img` stayed at 0 through a *successful* upload while
  the document-wide image count went 26 -> 30.

Keep `--stage` (rehearse everything except the irreversible click) as the
default way to prove the path, and never let `--publish` run when the image
failed to attach — a publish gate that refuses on a missing image is also what
lets you later prove a text-only post did not come from your own code.

### Closing the composer is a real step, and it is not one click

Measured 2026-10-12. A rehearsal that "closed without posting" left a **live
draft holding the post text**, one stray click from publishing. Three separate
causes, each of which reports success while doing nothing:

- **The close control has no button text.** On `/sharing/compose` it is
  `aria-label="Dismiss"`. A matcher over `textContent` alone finds nothing, the
  click never happens, and the function returns a clean-looking string. Match
  `aria-label` **and** `title` **and** `textContent`.
- **A discard confirmation can follow.** Handle
  `/^(discard|leave)$/i` after the dismiss, whether or not it appeared last time.
- **Dismissing is not clearing.** LinkedIn restores the draft into the feed's
  inline composer, so the text survives the close.

**Clear the editor only after the composer is closed, and bring the page
forward first.** Order matters and was measured both ways:

| attempt | result |
|---|---|
| `execCommand('delete')` while `/sharing/compose` is open | `ok=false`, all 1064 chars survive — with *and* without `bringToFront` |
| dismiss → `Page.bringToFront` → same call on the restored `/feed/` draft | `ok=true`, 1064 → 1 |

```python
s.ev(CLOSE_JS2)                 # aria-label/title/text match, then confirm
s.send("Page.bringToFront")     # a backgrounded tab silently drops execCommand
s.ev(CLEAR_EDITOR)              # select contents + document.execCommand('delete')
```

CDP `Input.dispatchKeyEvent` ctrl+A / Delete did **not** clear this ProseMirror
editor; the range-select + `execCommand` did. Use what measured, not what should
work.

### Which "is it closed?" check is worth running

Both obvious checks are broken on LinkedIn, in opposite directions:

- **`[role=dialog]` is permanent.** The page carries a hidden video.js
  `vjs-error-display vjs-modal-dialog`, so a dialog count reads true forever and
  reports a clean dismissal as `STILL OPEN`.
- **Editor presence is meaningless on `/feed/`.** The inline composer's
  `.tiptap.ProseMirror` always exists there. Measure **text**, not the node:

```js
[...document.querySelectorAll('.tiptap.ProseMirror')]
  .filter(e => (e.innerText || '').trim().length > 0).length   // 0 = clean
```

Count **trimmed** length: ProseMirror always keeps a trailing newline, so a
harmless `1` reads as a live draft and blocks a clean report.

Also note the composer opens as a **full page** at `/sharing/compose`
(`modal_count: 0` while `editor_present: true`), not a modal — a modal-scoped
probe is scoped to nothing.

And verify from a **separate** script reading the live DOM, not from the
rehearsal's own log: `editorsWithText: 0`, no attached file, no dialog.

### What the composer will accept

The file input's `accept` is
`image/jpeg,image/png,image/gif,image/webp,image/avif,image/bmp` — **images only**.
There is no "Add a document" control in this composer, so an owner who says
"I'll send an image or a PDF" cannot hand a PDF to this path. Send the PDF
converted to a page image (`pdftoppm`), or say plainly that the document post
needs LinkedIn's own attachment flow.

Confirm the attach actually rendered, not just that the input took the path:
locally attached files appear as `blob:` images (**measured 700x336 plus a
158x196 thumb**), so `input.files.length == 1` **plus** a `blob:` img is the
two-reading agreement that the preview is real.

### A dead CDP tab is not a site block

`Session.__init__` raising `CDP target '...' does not answer Runtime.evaluate —
dead tab, not a site block` after a long-lived Chrome has been up for days is
this, and the fix is one call — do not restart Chrome, which loses the logins:

```bash
curl -s -X PUT 'http://127.0.0.1:9222/json/new?https://www.linkedin.com/feed/'
```

Full session log, the wrong turns, and the exact scripts:
`references/linkedin-composer-cleanup.md`.

Full measured flow, the Playwright `connect_over_cdp` detour and why it bought
nothing here, the disproved `depth=1` hypothesis, and the diff-with-the-draft
method for confirming a live post is yours:
`references/linkedin-composer-raw-cdp.md`.

### Where raw CDP stops: destructive actions and dropdowns

The composer above is fully reachable by raw CDP `evaluate`, and
`connect_over_cdp` bought nothing for it. **Deleting a post did not work the
same way.** `el.click()` on the "..." control returned cleanly and mounted a
dropdown with `innerText.length == 0` and `childElementCount == 0` — an empty
shell, with `/delete/i` absent from `document.body.innerText`. A clean return
is not an opened menu.

Playwright's real `locator.click()` over the **same** Chrome (same login, no
second QR, never `browser.close()`) is what fills it — but it is not instant:
poll for the item and allow a second attempt before declaring it unavailable.

The role names are not the obvious ones, and both of the obvious ones fail
in a way that reads as success:

- the item is `DIV[role=button].feed-shared-control-menu__dropdown-item`
  containing `Delete post` — `get_by_role("menuitem")` returns **0** on a menu
  that is correctly open.
- the confirm lives in `.artdeco-modal`, not `[role=dialog]`. Scoping to
  `[role=dialog]` finds a **hidden video.js error modal** and reports
  `dialog: true` while `editorLen: 0`.

Two traps on the identity and the measurement:

- `[data-urn*="<id>"]`'s own `inner_text()` starts with the screen-reader
  label `Feed post number 1`. Read the hook from `.update-components-text`
  inside it, or the guard compares against a label and refuses forever.
- a modal left open from a failed attempt makes LinkedIn set `aria-hidden`, so
  Playwright's `get_by_role()` returns **0 for a button that is in the DOM**.
  Clear modals before measuring, or every subsequent count describes
  accessibility state rather than the page.

Verify a deletion with four independent readings (URN in `[data-urn]`, URN in
`body.innerText`, the opening sentence in the post texts, that sentence in
`body.innerText`) **plus** a post count, so an empty page cannot pass. Grepping
the probe log does not: `fastest typers` still matched a pre-existing older
post after both targets were gone.

Full flow, the five probes that looked right and were not, and the refusal
guard that must never fail open:
`references/linkedin-deleting-a-post.md`.

## Scripts

- `scripts/post_x_verified.js` — cookie-authenticated X text post via Playwright + JS click submit
- `scripts/post_x_image.js` — extend `post_x_verified.js` to attach media with hidden file input before submit
- `scripts/verify_profile.js` — scan profile timeline for exact posted text
- `scripts/verify_x_image.js` — profile scan helper for media posts

## References

- `references/x-post-workarounds.md` — session case log: browsers tried, failures, and method that finally worked
- `references/x-community-audience-picker.md` — the community audience picker end to end: the `aria-label`-only control, the `role="menuitem"` virtualized rows, `force=True` vs the mask, and the disabled-Post-button-in-flight signal
- `references/linkedin-composer-raw-cdp.md` — the LinkedIn composer end to end via raw CDP: the absent `[global-nav]` login probe, the DIV-with-empty-aria-label trigger, the tiptap contenteditable editor, the `Upload from computer` click that mounts the file input, `input.files.length` as the only reliable attach signal, and the stage/dry-run/publish split
- `references/linkedin-composer-cleanup.md` — leaving no trace after a rehearsal: the close control that is `aria-label="Dismiss"` with no button text, why dismissing does not clear the restored draft, the measured close-then-`bringToFront`-then-`execCommand('delete')` order, the two broken "is it closed?" checks, and the images-only `accept` list
- `references/linkedin-deleting-a-post.md` — deleting a post on LinkedIn: why synthetic `.click()` mounts an empty dropdown, the real item/modal selectors (`role=menuitem` and `[role=dialog]` are both wrong), the aria-hidden `get_by_role` trap, and four-way deletion verification
- `references/google-forms-radio-clicking.md` — why Google Forms radios ignore every synthetic click, and the accessibility-tree escalation that works

Full X composer selector table, the reply-dialog collision, the async
confirmation timings, and the passcode-gate trap: `x-community-posting` →
`references/x-composer-dom.md`.