---
name: x-outreach
description: Use when reaching prospects on X/Twitter via DM or search.
version: 1.0.0
tags: [x, twitter, outreach, dm, automation, prospecting]
related_skills: [x-automation, xurl, x-social-poster]
---

# X (Twitter) Outreach

Use this skill when the user asks to:
- send X/Twitter DMs to prospects
- find or qualify prospects on X
- build a repeatable X outreach campaign
- diagnose why X DMs are not being delivered

**This skill does NOT cover posting.** For posting/media/engagement use
`x-automation`. For official-API access use `xurl`.

## Read this before promising any volume

X outreach has hard platform ceilings that no amount of pacing changes.
Check them before quoting a number to the user.

| Path | Free limit | Notes |
|---|---|---|
| DMs from a web/browser session | **~20/day**, hard | No Premium. |
| DMs via official API | very low on basic tiers | Basic tier is write-limited; real volume needs pay-per-use |
| Follows | rate-limited, aggressive limits | Cheap to burn, easy to get restricted |
| Likes | rate-limited | |

The `~20/day` figure is the one that matters: it is well below the LinkedIn
figure people expect, and it is a **daily** cap, not a monthly one. Verify
the live number on the account rather than trusting this table, and report
what you actually observed.

## Backend choice — the real tradeoff

```
Official API (xurl)  → reliable, quota-bound, needs paid credits
Browser session      → cheap, ~20 DMs/day, breaks if session dies
Third-party APIs     → brittle, often violates ToS
```

Pick per task, and say which one you picked. A browser session is fine for a
handful of DMs; it is the wrong tool for a campaign.

## DM-closed accounts are the #1 delivery failure

A large share of X accounts have DMs closed to non-mutuals. On those, the
follow request is silently accepted-or-ignored and **the DM never lands** —
there is no error, no bounce, no failure notice. The send "succeeds" and
nothing arrives.

So a DM campaign that reports "N sent" is reporting nothing. Always verify
delivery, not dispatch:

- check the DM actually appears in Sent
- treat "no error" as **unconfirmed**, never as sent
- lead with "delivered" vs "dispatched" in any report to the user

## Prospect search patterns

Good search queries for B2B/tech outreach on X:

```
"need a developer" OR "looking for an agency" -filter:replies
"how do you handle" (manual|invoices|onboarding) lang:en
from:handle  # hiring / #building
```

The `lang:en` filter matters — without it a large share of results are
non-English and unusable for English outreach.

Lead with a hook that references something the person actually posted. A
generic DM referencing nothing specific reads as spam and is the main
reason DMs get ignored.

## Pacing

- 8-20s between DMs, randomised
- 30-60s after any send that returns an error
- Stop the run the moment a captcha/challenge appears. Do not "retry through
  it" — that is the behaviour that gets an account restricted.

## Verify before claiming

- **Never** report an outreach run as successful based on "no error returned".
  Absence of an error is not delivery, and for DM-closed accounts it is the
  expected result of a lost message.
- Only `xurl`/API output, or a screenshot of the Sent folder, proves a send.
- Report the count as *dispatched* and *confirmed-delivered* separately, and
  say when you could only measure the first.

## Community posting on X (measured 2026-09-29 on @Kunalsharmadec6)

Community posting is NOT broken and has never been. The control is easy to
miss because it carries **no `data-testid` at all**:

| Element | Selector |
|---|---|
| composer | `[data-testid^="tweetTextarea"]` (`tweetTextarea_0` on `/home`) |
| audience button | `button[aria-label="Choose audience"]` -> reads "Everyone" |
| after selecting | `button[aria-label="Change audience"]` -> text is the community name |
| community rows | `role="menuitem"`, nested in `[data-testid="cellInnerDiv"]` |
| post button | `[data-testid="tweetButtonInline"]` |

Three traps that each cost a wrong conclusion:

1. **`role="menuitem"`, not `menuitemradio`/`option`.** The rows live in a
   virtualized grid, so a scan for the "expected" roles finds nothing and it
   looks like the feature is absent.
2. **Rows need `click(force=True)`.** A `[data-testid="mask"]` intercepts
   pointer events and the click times out after 30s. Same shape as a sticky
   nav dropdown swallowing a click.
3. **A `disabled` post button is a stuck composer, not a failed post.** Check
   `is_disabled()` before typing; if it is already disabled with text staged,
   reload `/home` rather than waiting — it does not recover on its own.

**The left-hand community tab rail is a feed filter, not the audience.** It
looks exactly like an audience selector and silently does nothing to the post.

## The reply-dialog collision (cost a silently-lost reply)

Replying is NOT the same DOM as posting:

- The **home composer is also `[data-testid="tweetTextarea_0"]`**. A global
  query for it types into the feed *behind* the reply modal, and the dialog's
  Reply button stays `disabled` forever. Always scope to `[role="dialog"]`.
- The dialog's submit button is `[data-testid="tweetButton"]`, not
  `tweetButtonInline`.
- A real dispatch **closes the dialog**. That is the cheapest confirmation
  available — poll for the dialog going away rather than trusting a click.

## Confirmation is asynchronous

A post can be invisible at 6s and visible at 39s. Confirm by polling the
profile feed (`/HANDLE/with_replies` for replies, `/HANDLE` for posts) a few
times, not once. Checking once produces a false negative, which then gets
reported as a failed post.

## Anti-patterns

| Do not | Why |
|---|---|
| Bulk-DM a freshly scraped list | Low reply rate, high restriction risk, burns the account |
| Report "sent" from a 200 response | 200 = dispatched, not delivered |
| DM accounts with DMs closed | Message is silently discarded |
| Retry through a captcha | Fastest route to a locked account |
| Reuse one DM template | Reads as spam; the hook is the whole point |

## Related skills
- `x-automation` — posting, media upload, React composer quirks
- `xurl` — official X API CLI (post, DM, search, media)
- `x-social-poster` — Camofox-based posting
- `linkedin-outreach` — the LinkedIn equivalent, including its monthly
  personalized-invite quota
