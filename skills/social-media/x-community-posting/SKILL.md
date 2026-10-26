---
name: x-community-posting
description: |
  Posting to X communities via browser, and running paced X posting
  schedules without bursting them. Encodes the measured audience-picker DOM,
  async confirmation, rate-limit floors, and Premium-gated metrics.
version: 1.1.0
tags: [x, twitter, community, posting, automation, scheduling]
---

# X Community Posting

Posting to an X community. Read this before concluding that community posting
does not work — it does, and the obvious selectors all miss it.

Use this skill when:
- posting to an X community via browser automation
- building or debugging a recurring/paced X posting schedule
- a post did not appear where expected, or you suspect a control is missing

`x-outreach` covers DMs, `x-automation` covers general posting. This file
covers the **audience** path, which neither documents, plus the pacing rules
for a repeated-posting plan.

## The core fact

**You cannot post from a community page.** `/i/communities/<id>/latest` renders
**zero `[contenteditable]` elements** and no composer at all. Verified on four
communities. Absence of a composer there is not a broken feature.

You post from the home timeline with the community set as the **audience**.

## Three traps, each of which silently yields an `Everyone` post

1. **The audience button has no `data-testid`.** It is only
   `button[aria-label="Choose audience"]`, and reads `Everyone` until changed.
   Any selector keyed on `data-testid$="addAudience"` returns `0` — that is a
   selector miss, not a broken feature. Most X controls expose only
   `aria-label`; always dump the live control list before concluding absence.

2. **The community list is a virtualized grid.** Rows are **`role="menuitem"`**
   — not `menuitemradio`, not `option` — nested in
   `div[data-testid="cellInnerDiv"]`. Scanning only radio-ish roles finds
   nothing and looks like an empty list.

3. **A normal `click()` on a row times out after 30s.** A modal
   `[data-testid="mask"]` intercepts pointer events. Use **`click(force=True)`**.
   Clear the mask with Escape first, or the next interaction fails the same way.

4. **The picker mounts only a SLICE of your communities.** Measured visible on
   first open: Build in Public, Indie Hackers, SaaS & AI, Indiemakers, Branding.
   `Bootstrapped Startup Founders` was absent and a plain scan returned
   `community row not found` — **indistinguishable from "you are not a member"**.
   After the direct scan misses: type into the picker's own search input and
   re-scan, then `mouse.wheel(0, 420)` to scroll the virtualized grid and
   re-scan each time. All three verified working.

## Working sequence

```python
pg.goto("https://x.com/home", wait_until="domcontentloaded")
box = pg.wait_for_selector('[data-testid^="tweetTextarea"]', timeout=45000)
box.click()
aud = pg.wait_for_selector('button[aria-label="Choose audience"]', timeout=25000)
aud.click()
pg.wait_for_timeout(4000)                      # list is slow; wait it out
for m in pg.query_selector_all('[role="menuitem"]'):
    if (m.inner_text() or '').strip().startswith(COMMUNITY):
        m.click(force=True)                   # mask blocks a normal click
        break
pg.wait_for_timeout(3000)
cur = (pg.query_selector('button[aria-label="Change audience"]')
       or pg.query_selector('button[aria-label="Choose audience"]'))
assert (cur.inner_text() or '').strip() == COMMUNITY   # assert BEFORE typing
```

Then type with `pg.keyboard.type(text, delay=40)` and post via
`[data-testid="tweetButtonInline"]`.

## Verify the audience, not just the click

Re-read the audience button **immediately before** posting. A post staged
without it publishes as `Everyone`, renders fine in your profile, and looks
like a success. Confirm by permalink:

```
the post's article must contain an <a href^="/i/communities/">
```

If the profile shows the post but the community's Latest feed does not, the
audience never took. Check the article's links — that is the ground truth, not
the URL you posted from.

## Replying is a different DOM, and the collision is silent

Posting and replying share the testid `tweetTextarea_0`. A global query for
the composer types into the feed **behind** the reply modal, leaving the
dialog's Reply button `disabled` forever. The click throws no error and no
reply is posted — a script will happily report success.

- scope every reply interaction to `[role="dialog"]`
- the dialog's submit button is `[data-testid="tweetButton"]`, **not**
  `tweetButtonInline`
- a real dispatch **closes the dialog** — poll for that instead of trusting
  the click

## Confirm asynchronously, and on the right surface

A post was invisible at 6s and visible at 39s. Poll the profile feed
(`/HANDLE` for posts, `/HANDLE/with_replies` for replies) a few times.

Worse, verify against the surface the thing lives on. A post declared
"failed" was absent from the *community* feed while live on the *profile* the
whole time — the user corrected it. The same mistake made an inbox look
empty when a passcode-recovery page was intercepting it.

Full selector table and the measured traps: `references/x-composer-dom.md`.

## The tab rail is not the audience

The left-hand community tab rail only **filters the feed**. Clicking "SaaS & AI"
then posting sends to `Everyone`. This is the most common way to believe you
posted to a community when you did not.

## Stale Post button

`[data-testid="tweetButtonInline"]` reporting `disabled: True` with text staged
and the audience correct means X is mid-publish from a prior attempt. Reload
`/home` and redo the whole sequence. Do not force the click.

## Account identity matters

Confirm **which account** the browser is on before posting. On 2026-09-29 the
X session was `@Kunalsharmadec6` while a separate **"Kawaki Studios"** account
also existed and had its own posting history. Brand posts made from the
personal account land on the wrong profile and read as an impersonation risk.
Check the account switcher / self-link, not the tab title.

## Do not burst a posting schedule (user correction 2026-09-30)

Asked to "start posting" on a plan with slots every 2 hours, I ran every
overdue slot in one call: **5 posts inside 5 minutes** plus 7 replies. The
user asked why so many had gone out at once. That was my call, and it was
wrong — community posting is the *most* rate-sensitive surface on X, and a
cluster of posts in one burst is the shape that gets a community member
flagged or an account throttled.

- **One post per invocation.** A community slot is a slot, not a quota to
  fill. Never drain a backlog to "catch up".
- Keep a hard floor between posts, measured on the **live profile** (a local
  state file is bypassed by a manual send, which is how the burst happened).
  90 minutes is a sane default.
- Scope the floor's timestamp read to the **first `<article>`**. A page-wide
  `·\s*(\d+)(s|m|h|d)` regex also matches engagement counters, so a
  just-published post reads as "1 min ago" from its own reply count and the
  floor passes when it should have blocked. This failed its first test.
- A missed community window is simply missed. Say so and move on.

Script: `outreach-automation` → `scripts/x_pacing_floor.py`.

## Gate content pools on dates, not just style (user correction 2026-09-30)

The user reported: *"You posted a post saying 2024 its 2026."* A pooled post
reading **"Agencies that survived 2024"** had published verbatim — two years
stale, in the account's own voice. It had drawn 2 replies and 6 likes before it
was caught, the best engagement of the day.

Nothing flagged it. The pool gate checked length, hashtags, corporate tells and
hooks. **No gate ever looked at a date**, because dates are the one claim in a
post that silently decays while every other check keeps passing.

- Reject any post containing a year `!= current_year`. This is the check that
  matters; it is one regex.
- Decaying relative phrases ("last year", "two years ago", "back in the day")
  are worth flagging too, but **keep the list narrow**. "in the last year" is
  relative and stays true forever — catching it over-blocks a good post, and
  over-blocking a pool is its own failure. Prefer explicit years.
- Quarantine by moving the file **out of the scheduled glob**, not by renaming.
  A `.txt` anywhere in the pool directory is still schedulable.
- Prove the gate catches the known-bad case before trusting it: copy the
  offending file back in, assert it fails, remove it.

## A green run is not a working system

Measured 2026-09-30: the X loop was repaired, verified end-to-end, and reported
fixed. It was dead again within 30 minutes, and **nobody noticed for 90
minutes** — three consecutive ticks failed silently. The user had to ask "what
about X" to surface it.

An unattended timer that writes nothing produces **no error**. The log simply
stops. That is the failure mode to design against.

- **After any fix, re-check one full cycle later.** "It worked once" is not "it
  works". A repair verified in the same breath it was made proves nothing about
  the next scheduled run.
- When reporting on an automated channel, quote **the most recent completed
  cycle**, not the last one you watched succeed. If the most recent is stale, say
  so first.
- If the user has to ask whether a loop is alive, the loop has already failed its
  only real test.

## Report Premium-gated metrics as unmeasurable

`x.com/i/account_analytics` returns "Advanced analytics with X Premium —
Upgrade to continue" on a free account; `analytics.x.com/user/<h>/posts` 404s.
Per-post counters render as bare numbers with no labels, so a parse yields
`None`. `None` is **not zero engagement**. Report replies/reposts/likes, name
impressions and reach as Premium-gated, and never infer reach from how much
you posted.

## Anti-patterns

| Do not | Why |
|---|---|
| Look for a composer on `/i/communities/<id>` | There is none; the feature works, the page does not |
| Select a community tab and post | Tabs filter the feed; they do not set audience |
| Trust `data-testid` absence as feature absence | The audience control is `aria-label` only |
| Skip the pre-post audience assert | Publishes as `Everyone` and looks successful |
| Trust "the click landed" | Verify via the permalink's `/i/communities/` link |
| Scan once for a community row | The picker is virtualized; search or scroll before concluding |
| Query `tweetTextarea_0` globally when replying | Types into the feed behind the modal; scope to `[role="dialog"]` |
| Verify on one page only | Check every surface it could be on before reporting absence |
| Call a selector miss a broken feature | The audience control is `aria-label`-only; a testid search never matches it |
| Fire a whole schedule backlog at once | Community slots are rate-sensitive; 5 posts in 5 min reads as automation |
| Gate a pool on style alone | A stale year ships as fact; style checks pass forever on rotting content |
| Report a loop fixed right after fixing it | Verified once ≠ works on the next unattended cycle |
| Report a `None` counter as zero | Premium gates impressions/reach; `None` means unmeasurable |
